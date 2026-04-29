# Service 0x19 ReadDTCInformation — 用例生成规则

## 服务概述

- **Service ID**: 0x19
- **Service Name**: ReadDTCInformation
- **正响应 SID**: 0x59（0x19 + 0x40）
- **负响应格式**: `7F 19 <NRC>`
- **无 Subfunction 概念但有子功能编号**（0x01/0x02/0x04/0x06/0x0A 等），SPRMIB 不适用
- **关键特性**: 各子功能有不同的请求/响应格式；需要 DTC 表数据支撑；需按逐 DTC 生成故障注入用例

### 各子功能正响应格式

| 子功能 | 名称 | 请求格式 | 正响应格式 |
|--------|------|---------|-----------|
| 0x01 | ReportNumberOfDTCByStatusMask | `19 01 <DTCStatusMask>` | `59 01 <AvailabilityMask> <NumberOfDTC_H> <NumberOfDTC_L>` |
| 0x02 | ReportDTCByStatusMask | `19 02 <DTCStatusMask>` | `59 02 <AvailabilityMask> <DTC_3bytes> <Status_1byte> [...]` |
| 0x04 | ReportDTCSnapshotRecordByDTCNumber | `19 04 <DTC_3bytes> <SnapshotRecordNumber>` | `59 04 <DTC_3bytes> <Status> <SnapshotRecordNumber> <data>` |
| 0x06 | ReportDTCExtendedDataRecordsByDTCNumber | `19 06 <DTC_3bytes> <ExtendedDataRecordNumber>` | `59 06 <DTC_3bytes> <Status> <RecordNumber> <data>` |
| 0x0A | ReportSupportedDTCs | `19 0A FF` | `59 0A <DTCStatusAvailabilityMask> <DTC_3bytes> <Status> [...]` |

### 典型 NRC

| NRC  | 含义 | 触发条件 |
|------|------|---------|
| 0x12 | Subfunction Not Supported | 发送了 0x19 不支持的子功能 |
| 0x13 | Incorrect Message Length Or Invalid Format | 报文长度错误 |
| 0x31 | Request Out Of Range | DTC 编号或 Record Number 越界 |
| 0x7F | Service Not Supported In Active Session | 当前会话下不支持 0x19 服务 |

---

## 生成分类（共 7 类）

按以下固定顺序逐类生成，每个分类之间用 `--service ID 0x19 <分类名>` 分隔。

### 软件域规则

**必须为每个存在 0x19 服务的软件域独立生成完整用例集。**

- Application / App 域：从 `ApplicationServices` Sheet 读取
- Boot / BootLoader 域：从 `BootServices` Sheet 读取（若存在 0x19 行）

若 Boot 域存在 0x19 数据，则为 Boot 域单独生成 Physical + Functional（如支持）的完整用例。

### 寻址方式规则

**即使参数表 `Functional Request = N`，仍需生成完整的 Functional 寻址用例集。** 此时所有 Functional 用例的预期输出统一为 `Check No_Response Within[1000]ms;`。

---

### 分类 1: Session Layer Test
#### 用例数量规则

- `Nmask` = 需测试的 DTCStatusMask 值数量（通常为 3：FF / 0x08 / 0x09）
- `Npos` = 支持的子功能（0x01/0x02） × 支持的会话数 × Nmask
- `Npos_0A` = 0x0A 子功能 × 支持的会话数（0x0A 不区分 Mask）
- `Nneg_sf` = 不支持的子功能 case 数
- `Nneg_sess` = 不支持的会话 case 数
- **总数 = Npos + Npos_0A + Nneg_sf + Nneg_sess**

> **关键规则**：对于 0x01 和 0x02 子功能，**必须测试多个 DTCStatusMask 值**：
> - `FF`（查询所有状态位）
> - `0x08`（仅查询 confirmedDTC，bit3=1）
> - `0x09`（查询 testFailed 或 confirmedDTC，bit0+bit3）
>
> 这些 Mask 值来自输入表 `GroupOfDTC` 中被标记为 `Support=Y` 的状态位组合。

#### 用例命名规则

- 正向：`<CurrentSessionName> Session support the 0x19 service 0x<Sub> subfunction`
  - 示例：`Extended Session support the 0x19 service 0x02 subfunction`
- 负向（会话不支持）：`<CurrentSessionName> Session nonsupport 0x19 services`
  - 示例：`Default Session nonsupport 0x19 services`
- 负向（子功能不支持）：`0x19 service nonsupport 0x<Sub> subfunction`
  - 示例：`0x19 service nonsupport 0x03 subfunction`

#### 测试步骤模板

**A. 当前会话不支持 0x19 服务（负向）**
```
1. 进入 <CurrentSessionNotSupport>（通常为 Default）
2. Send DiagBy[Physical]Data[19 <RepSub> <DTCStatusMask>];
```

**B. 支持子功能正向（需 DTC 数据的子功能）**
```
1. 进入 <CurrentSessionSupport>（通常为 Extended）
2. Stop MsgCycle[<FaultMsgId>];
3. Delay[3000]ms;
4. Send DiagBy[Physical]Data[19 <Sub> <DTCStatusMask>];
5. Send MsgCycle[<FaultMsgId>];
```

**C. 支持子功能正向（不需 DTC 数据的子功能如 0x01/0x0A）**
```
1. 进入 <CurrentSessionSupport>（通常为 Extended）
2. Send DiagBy[Physical]Data[19 <Sub> <DTCStatusMask>];
```

**D. 子功能不支持（负向）**
```
1. 进入 <CurrentSessionSupport>（通常为 Extended）
2. Send DiagBy[Physical]Data[19 <UnsupportedSub> <DTCStatusMask>];
```

#### Check 规则

**A. 当前会话不支持服务：**
- `Check DiagData[7F 19 7F]Within[50]ms;`

**B. 支持子功能正向（有 DTC 数据）：**
- 0x01: `Check DiagData[59 01 <AvailabilityMask> <N_DTC_H> <N_DTC_L>]Within[50]ms;`
- 0x02: `Check DiagData[59 02 <AvailabilityMask> <DTC_H> <DTC_M> <DTC_L> <Status>]Within[50]ms;`
- 0x04: `Check DiagData[59 04 <DTC_3bytes> <Status> <RecordNum> <SnapshotData>]Within[50]ms;`
- 0x06: `Check DiagData[59 06 <DTC_3bytes> <Status> <RecordNum> <ExtData>]Within[50]ms;`

**C. 支持子功能正向（无 DTC 数据）：**
- 0x0A: `Check DiagData[59 0A <DTCStatusAvailabilityMask> <DTC_3bytes> <Status> ...]Within[50]ms;`

**D. 子功能不支持：**
- `Check DiagData[7F 19 12]Within[50]ms;`

#### 特殊规则

1. DTCStatusMask 通常使用 FF（查询所有状态位）
2. Snapshot Record Number: 01=首次故障, 02=最近故障, FF=全部
3. 扩展数据（0x06）包含: Occurrence Counter + Timestamp(Y/M/D/H/M/S) + Odometer + Voltage + Speed
4. 若 DTC 快照表为空，0x04 子功能可能返回空数据
5. 有 DTC 数据的子功能（0x02/0x04/0x06）需先制造故障再读取
6. 无 DTC 数据的子功能（0x01/0x0A）可直接读取

---

### 分类 2: SPRMIB Test
#### 用例数量规则

- 设 `R` = 支持的会话集合
- 设 `T` = 支持的子功能集合
- **总数 = |R| × |T|**

> **关键规则**：0x19 无 Subfunction 概念，SPRMIB 不适用。但需验证发送 suppress bit（0x8x）时 ECU 的行为。
> 参考模板确认：所有 0x19 子功能发送 `0x80 + Sub` 均返回 NRC 0x12。

#### 用例命名规则

- `<SessionName> session 0x19 service does not support the suppress bit`

#### 测试步骤模板

```
1. 进入 <CurrentSession>
2. Send DiagBy[Physical]Data[19 <0x80 + Sub> <DTCStatusMask>];
```

例如：
- `19 81 FF`（0x01 + suppress bit）
- `19 82 FF`（0x02 + suppress bit）
- `19 8A`（0x0A + suppress bit）

#### Check 规则

- 第 2 步：`Check DiagData[7F 19 12]Within[50]ms;`

#### 特殊规则

1. 0x19 所有子功能的 SPRMIB=N，suppress bit 不被支持
2. 发送 `0x80 + Sub` 被视为不支持的子功能，统一返回 NRC 0x12
3. 需覆盖所有支持的子功能（01/02/0A）和支持的会话

---

### 分类 3: DTC Read Function Test

#### 用例数量规则

**核心规则：为 DTC 表中每个 Support=Y 的 DTC 生成 2 条用例。**

| 状态 | 数量 | 说明 |
|------|------|------|
| t-09（故障活跃态） | N_dtc | status=0x09（bit0 testFailed=1 + bit3 confirmedDTC=1） |
| t-08（故障恢复态） | N_dtc | status=0x08（bit0 testFailed=0 + bit3 confirmedDTC=1） |

**总数 = N_dtc × 2**

其中 N_dtc = DTC 表中 Support=Y 的 DTC 数量。

> **关键规则**：每个 DTC 必须单独生成独立的故障注入+读取用例，不能合并。每个 DTC 有其特定的故障注入方法。

#### 用例命名规则

- 活跃态：`<DTCFaultDescription> t-09 state\nDTC:<DTC_Hex>`
- 恢复态：`<DTCFaultDescription> t-08 state\nDTC:<DTC_Hex>`

例如：
- `Steering wheel left zone MAT open circuit fault-09 state\nDTC:0x5D8313`
- `Steering wheel left zone MAT open circuit recovery-08 state\nDTC:0x5D8313`

#### 测试步骤模板

**A. 故障活跃态（t-09）：**
```
1. 进入 Default 会话
2. <DTC_FaultInjection_Method>
3. Delay[<FaultActivation_Delay>]ms;
4. Send DiagBy[Physical]Data[19 02 FF];
5. Delay[<ReadInterval>]ms;
6. Send DiagBy[Physical]Data[19 02 FF];
```

**B. 故障恢复态（t-08）：**
```
1. 进入 Default 会话
2. <DTC_FaultInjection_Method>
3. Delay[<FaultActivation_Delay>]ms;
4. Send DiagBy[Physical]Data[19 02 FF];
5. <DTC_FaultRecovery_Method>
6. Delay[<Recovery_Delay>]ms;
7. Send DiagBy[Physical]Data[19 02 FF];
8. Delay[<ReadInterval>]ms;
9. Send DiagBy[Physical]Data[19 02 FF];
10. Send DiagBy[Physical]Data[14 FF FF FF];
11. Send DiagBy[Physical]Data[19 02 FF];
```

其中：
- `<DTC_FaultInjection_Method>` = 每个 DTC 的具体故障注入方式，从输入表 DTC 列读取
  - 电压类：`Set Voltage[7.5]V`（欠压）/ `Set Voltage[17.5]V`（过压）
  - 信号类：`Steering wheel left zone MAT open circuit`（实际测试中使用对应信号操作）
  - 通讯类：`Set LIN BIT-ERROR` / `Set LIN CHECKSUM-ERROR` 等
- `<DTC_FaultRecovery_Method>` = 故障恢复操作
- `<FaultActivation_Delay>` = 故障生效延时（通常 150-550ms，按 DTC 特性调整）
- `<ReadInterval>` = 读取间隔（通常 60-70ms）
- `<Recovery_Delay>` = 恢复延时（通常 150-450ms）

#### Check 规则

**A. 故障活跃态（t-09）：**
- 第 4 步：`Check DiagData[59 02 09 00 00 00 00]Within[200]ms;`（故障尚未触发，可能返回空）
- 第 6 步：`Check DiagData[59 02 09 <DTC_H> <DTC_M> <DTC_L> 09]Within[200]ms;`（故障已触发，status=0x09）

**B. 故障恢复态（t-08）：**
- 第 4 步：`Check DiagData[59 02 FF <DTC_H> <DTC_M> <DTC_L> 09]Within[200]ms;`（故障活跃中）
- 第 7 步：`Check DiagData[59 02 FF <DTC_H> <DTC_M> <DTC_L> 09]Within[200]ms;`（仍活跃）
- 第 9 步：`Check DiagData[59 02 FF <DTC_H> <DTC_M> <DTC_L> 08]Within[200]ms;`（已恢复，status=0x08）
- 第 10 步：`Check DiagData[54]Within[200]ms;`（清除 DTC）
- 第 11 步：`Check DiagData[59 02 FF 00 00 00 00]Within[200]ms;`（清除后为空）

#### 特殊规则

1. **每个 DTC 单独一条用例**，不可合并多个 DTC 到一条用例中
2. **同一个 DTC 号的不同故障类型**（如 LIN 通讯的 BIT-ERROR / CHECKSUM-ERROR / PARITY-ERROR）各生成独立用例
3. DTC 编号从 DTC 表读取，为 3 字节（如 `5D 83 13`）
4. 故障注入方法从 DTC 表或项目定义的故障列表中读取
5. **参考模板统一在 Default 会话下测试**，不切换到 Extended
6. 响应超时使用 `Within[200]ms`（比常规 50ms 更长），因为故障注入后 ECU 处理可能延迟

---

### 分类 4: Incorrect Diagnostic Command Test
#### 用例数量规则

**固定 2 条 / 每种支持的寻址方式**

| 序号 | 错误类型 | 描述 |
|------|---------|------|
| 1 | SF_DL > 合法值 | 有效负载长度大于合法值 |
| 2 | SF_DL < 合法值 | 有效负载长度小于合法值 |

> **注意**：客户当前参考模板中 **不包含 DLC 错误测试**（DLC < 8 / DLC > 8），只测 SF_DL 异常。

#### 用例命名规则

1. `Valid SF_DL=<legal>, invalid SF_DL > <legal>, and those with invalid equivalence class SF_DL=<value> NegativeCase-$19`
2. `Valid SF_DL=<legal>, invalid SF_DL < <legal>, and those with invalid equivalence class SF_DL=<value> NegativeCase-$19`

其中 `<legal>` 随子功能变化：0x01/0x02/0x0A=2

#### 测试步骤模板

选择一个代表性子功能（优先 0x01）进行测试。

**前置步骤：** 进入支持 0x19 的当前会话（通常 Extended 或 Default）

**A. SF_DL > 合法值**
```
Send DiagBy[<Addr>]Data[19 01]WithLen[5];
```

**B. SF_DL < 合法值**
```
Send DiagBy[<Addr>]Data[19 01]WithLen[1];
```

#### Check 规则

| 错误类型 | Expected Output |
|---------|----------------|
| SF_DL > 合法值 | `Check DiagData[7F 19 13]Within[50]ms;` |
| SF_DL < 合法值 | `Check DiagData[7F 19 13]Within[50]ms;` |

---

### 分类 5: Functional Addressing Test

#### 用例数量规则

**无论参数表 `Functional Request` 为何值，都生成完整的 Functional 寻址用例集。**

- 复制 Session Layer Test 中所有正向用例（支持的子功能 × 支持的会话 × DTCStatusMask）
- 再加上 Incorrect Diagnostic Command 的 Functional 版
- **总数 = Session Layer 正向数 + Incorrect 数**

#### 用例命名规则

沿用 Session Layer 命名，发送寻址方式改为 `[Function]`/`[Funcation]`

#### 测试步骤模板

与 Session Layer 相同，但 `[Physical]` 改为 `[Function]`/`[Funcation]`

#### Check 规则

**当 `Functional Request = N` 时：**
- 所有 Functional 用例统一：`Check No_Response Within[1000]ms;`

**当 `Functional Request = Y` 时：**
- 与 Physical 相同的 Check 规则

#### 特殊规则

1. 即使 Functional Request=N，仍需为所有支持的子功能×会话生成 Functional 用例
2. Case ID 中 `Phy` 改为 `Fun`，编号继续 Phy 编号递增
3. Incorrect Command 的 Functional 版也需生成

---

## 会话进入标准路径

为统一生成，进入各会话的标准路径如下：

| 目标会话 | 标准进入步骤 |
|---------|------------|
| Default（0x01） | `Send DiagBy[Physical]Data[10 01];` |
| Extended（0x03） | `Send DiagBy[Physical]Data[10 01];` → `Delay[1000]ms;` → `Send DiagBy[Physical]Data[10 03];` |
| Programming（0x02） | `Send DiagBy[Physical]Data[10 01];` → `Delay[1000]ms;` → `Send DiagBy[Physical]Data[10 03];` → `Send DiagBy[Physical]Data[10 02];` |

---

## 功能寻址用例生成规则

**无论 `Functional Request` 是否支持，都必须生成 Functional 寻址用例。**

当 `Functional Request = N` 时：
1. 复制 Session Layer 所有正向用例，`[Physical]` 改为 `[Function]`
2. 所有 Expected Output 统一改为 `Check No_Response Within[1000]ms;`
3. Case ID 中 `Phy` 改为 `Fun`，编号继续 Phy 编号递增
4. Incorrect Command 的 Functional 版也需生成

当 `Functional Request = Y` 时：
1. 复制所有 Physical 用例
2. `[Physical]` 改为 `[Function]`
3. Expected Output 与 Physical 相同

---

## 生成注意事项

1. **Case ID 不可重复**，物理寻址 `Diag_0x19_Phy_001` 起递增
2. **编号从 001 开始**，优先编写所有 Physical 用例，Functional 编号继续递增
3. **每个 Send 都要有对应 Check**，除以下豁免：
   - `Delay[...]ms` 不写 Check
   - 带 `AndCheckResp[...]` 的发送函数不单独写 Check
4. **DTC 编号格式为 3 字节**（如 5D 83 13），从 DTC 表读取
5. **Session Layer 须测试多个 DTCStatusMask**（FF / 0x08 / 0x09），来自 GroupOfDTC 支持的 bit 位
6. **不同子功能的合法 SF_DL 不同**，Incorrect Command 测试需标注合法值
7. **DTC Read 必须按逐 DTC 生成**，每个 DTC 生成 t-09 活跃态 + t-08 恢复态各 1 条
8. **输出格式严格按照 Case ID / Case名称 / 测试步骤 / 预期输出 的固定模板**
9. **Functional 寻址无论是否支持都必须生成全套用例**

### 分类 6: NRC Priority Test
#### 用例数量规则

**固定 1 条 / 每个软件域 / 物理寻址**

> 根据输入表 NRC 优先级链（如 `0x13>0x12>0x31`），只生成 1 条验证最高优先级 NRC 的用例。

#### 用例命名规则

`NRC <NRC_Priority_Chain>`

例如：`NRC 13>12>31`

#### 测试步骤模板

```
1. 进入支持的会话（通常 Extended）
2. Send DiagBy[Physical]Data[19 <UnsupportedSub> <Data>]WithLen[<InvalidLen>];
```

构造方法：选择不支持的子功能（触发 NRC 0x12），同时设置非法长度（触发 NRC 0x13），ECU 应返回优先级最高的 NRC 0x13。

#### Check 规则

- 第 2 步：`Check DiagData[7F 19 13]Within[50]ms;`（返回优先级最高的 NRC）

#### 特殊规则

1. 只生成 1 条，不需要为每个 NRC 组合都生成
2. 验证的核心：当多个 NRC 条件同时满足时，ECU 返回优先级最高的那个

---

## 分类总览

0x19 固定 7 类生成能力（按顺序）：

| 分类 | 名称 | 说明 |
|------|------|------|
| 1 | Session Layer Test | 多 DTCStatusMask（FF/0x08/0x09）× 子功能 × 会话 |
| 2 | SPRMIB Test | 验证 suppress bit 返回 NRC 0x12 |
| 3 | DTC Read Function Test | 逐 DTC 生成，每个 DTC 2 条（t-09 + t-08） |
| 4 | Incorrect Diagnostic Command Test | 固定 2 条（仅 SF_DL 异常） |
| 5 | Functional Addressing Test | 无论 Functional Request 是否支持都生成全套 |
| 6 | NRC Priority Test | 固定 1 条/域/Physical |
| 7 | Boot Domain Test | Boot 域独立生成（若存在 0x19 数据） |

生成条数由以下因素共同决定：
- 支持的子功能集合
- 支持的会话集合
- DTCStatusMask 组合
- DTC 列表（Support=Y 的每个 DTC 各 2 条）
- 软件域（App / BootLoader）
- Functional Request 状态