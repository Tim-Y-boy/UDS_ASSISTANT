# Service 0x28 CommunicationControl — 用例生成规则

## 服务概述

- **Service ID**: 0x28
- **Service Name**: CommunicationControl
- **正响应 SID**: 0x68（0x28 + 0x40）
- **负响应格式**: `7F 28 <NRC>`
- **请求格式**: `28 <Sub> <communicationType>`
- **子功能**: 0x00(EnableRxAndTx), 0x01(EnableRxAndDisableTx), 0x02(DisableRxAndEnableTx), 0x03(DisableRxAndTx)
- **communicationType**: 01=NormalMsg, 02=NetworkMgmt, 03=Both
- **合法 SF_DL**: 3 字节
- **关键特性**: 禁用/启用报文发送，需配合 `Check MsgInexist`/`Check MsgExist` 验证

### 正响应格式

- `68 <Sub>`（仅确认，无额外 payload）

### 典型 NRC

| NRC  | 含义 | 触发条件 |
|------|------|---------|
| 0x12 | Subfunction Not Supported | 发送了不支持的子功能 |
| 0x13 | Incorrect Message Length Or Invalid Format | 报文长度错误（SF_DL ≠ 3） |
| 0x22 | Conditions Not Correct | 前置条件不满足 |
| 0x31 | Request Out Of Range | communicationType 不支持 |
| 0x7E | Subfunction Not Supported In Active Session | 该子功能在当前会话下不支持 |
| 0x7F | Service Not Supported In Active Session | 当前会话下不支持 0x28 服务 |

---

## 软件域规则

- **必须为 APP 和 Boot 两个软件域各独立生成完整用例集**
- APP 域使用 ApplicationServices 表的 0x28 服务行
- Boot 域使用 BootServices 表的 0x28 服务行
- 若 Boot 域不支持 0x28，仍需生成负向用例（Boot 所有测试预期 7F 28 7F）
- 两个域的用例集之间用注释行分隔，Boot 域用例编号接续 APP 域

## 寻址规则

- **Physical 寻址**：生成完整测试集
- **Functional 寻址**：无论是否支持 Functional Request，均生成完整的功能寻址用例集
- Functional 寻址用例集中，所有测试步骤使用 `[Function]` 发送，所有预期输出为 `Check No_Response Within[1000]ms;`
- 功能寻址用例集是物理寻址用例集的完整镜像

---

## 生成分类（共 9 类）

按以下固定顺序逐类生成，每个分类之间用 `--service ID 0x28 <分类名>` 分隔。

---

### 分类 1: Session Layer Test (APP)

#### 用例数量规则

- **正向用例**: 每个支持的会话 × 每个支持的子功能 × 每个支持的 communicationType 各 1 条
  - 同时包含不支持的子功能/communicationType 的负向验证
- **负向用例（不支持会话）**: 每个不支持的会话，选取代表性子功能×communicationType 组合各 1 条
- **总数 = Npos + Nneg**

#### 生成顺序

按会话分组：
1. Default Session 负向（不支持 0x28）：选取代表性组合
2. Programming Session 负向（如不支持）：选取代表性组合
3. Extended Session 正向：每个支持的子功能 × communicationType 组合
4. Extended Session 负向（不支持的子功能/communicationType）

#### 用例命名规则

- 正向：`<CurrentSessionName> Session support the 0x28 service 0x<Sub> subfunction control <CommTypeDesc> PositiveResponseCase-$28`
  - 示例：`Extended Session support the 0x28 service 0x00 subfunction control normal communication messages sending and receiving PositiveResponseCase-$28`
- 负向（会话不支持）：`<CurrentSessionName> Session nonsupport service 0x28 NegativeCase-$28`
- 负向（子功能不支持）：`Extended Session nonsupport 0x28 service 0x<Sub> subfunction NegativeCase-$28`

#### 测试步骤模板

**A. 不支持的会话（Default）**
```
1. 进入 Default 会话
2. Send DiagBy[Physical]Data[28 <Sub> <CommType>];
（可合并多个 CommType 在同一用例中）
```

**B. 不支持的会话（Programming）**
```
1. Send DiagBy[Physical]Data[10 01];
2. Send DiagBy[Physical]Data[10 03];
3. Send DiagBy[Physical]Data[31 01 02 03];
4. Send DiagBy[Physical]Data[10 02];
5. Send DiagBy[Physical]Data[28 <Sub> <CommType>];
```

**C. 支持会话正向**
```
1. 进入 Extended 会话
2. Send DiagBy[Physical]Data[28 <Sub> <CommType>];
```

**D. 支持会话中不支持的子功能**
```
1. 进入 Extended 会话
2. Send DiagBy[Physical]Data[28 <UnsupportedSub> <CommType>];
```

#### Check 规则

**A. 不支持的会话：**
- `Check DiagData[7F 28 7F]Within[50]ms;`

**B. Programming 不支持：**
- `Check DiagData[7F 28 7F]Within[50]ms;`

**C. 支持会话正向：**
- `Check DiagData[68 <Sub>]Within[50]ms;`

**D. 不支持的子功能：**
- `Check DiagData[7F 28 12]Within[50]ms;`

#### 特殊规则

1. 每个用例可包含多个 CommType 的测试步骤（如 01 和 03）
2. Programming Session 进入路径：`10 01 → 10 03 → 31 01 02 03 → 10 02`
3. 子功能 0x01(EnableRxAndDisableTx) 和 0x02(DisableRxAndEnableTx) 若不支持，返回 NRC 0x12
4. communicationType 支持列表从参数表读取

---

### 分类 2: Secure Access Test (APP)

#### 用例数量规则

- 对每个支持的子功能 × 每个支持的 communicationType 组合各 1 条（解锁后测试）
- **总数 = Nsub_comm combos with security**

#### 用例命名规则

`Security access Lx unlock supports support 0x28 service 0x<Sub> subfunction control <CommTypeDesc> PositiveResponseCase-$28`
- 示例：`Security access L1 unlock supports support 0x28 service 0x00 subfunction control normal communication messages sending and receiving PositiveResponseCase-$28`

#### 测试步骤模板

```
1. 进入支持的会话（Extended）
2. Send DiagBy[Physical]Data[27 <SeedSub>]AndCheckResp[PositiveResponse];
3. Send Security Right KeyBy[Physical]Level[<KeySub>];
4. Send DiagBy[Physical]Data[28 <Sub> <CommType>];
```

#### Check 规则

- 第 3 步：`Check DiagData[67 <KeySub>]Within[50]ms;`
- 第 4 步：`Check DiagData[68 <Sub>]Within[50]ms;`

#### 特殊规则

1. 安全等级从参数表 Access Level 字段读取
2. 覆盖所有支持的 sub×commType 组合
3. 即使 0x28 无安全限制（Access Level 为空），仍需生成本分类（使用最低安全等级）

---

### 分类 3: SPRMIB Test (APP)

#### 用例数量规则

- 不支持的会话（Default）：每个 SPRMIB 子功能 × commType 组合 → NRC
- 不支持的 SPRMIB 子功能（如 0x81/0x82 对应 0x01/0x02）：→ NRC 0x12
- 支持的 SPRMIB 子功能（如 0x80/0x83 对应 0x00/0x03）：→ No_Response
- **总数 = Nunsupported_session_combos + Nunsupported_sub_combos + Nsupported_sprmib_combos**

#### 生成顺序

1. Default Session SPRMIB 负向（所有 SPRMIB 子功能 × commType → 7F 28 7F）
2. Extended Session 不支持的 SPRMIB 子功能（0x81/0x82 → 7F 28 12）
3. Extended Session 支持的 SPRMIB 子功能（0x80/0x83 → No_Response）

#### 用例命名规则

- 负向（会话不支持）：`<SessionName> Session nonsupport service 0x28 with SPRMIB NegativeCase-$28`
- 负向（子功能不支持）：`Extended Session nonsupport 0x28 service 0x<Sub> subfunction with SPRMIB NegativeCase-$28`
- 正向：`Extended Session support 0x28 service 0x<Sub> subfunction control <CommTypeDesc> with SPRMIB PositiveResponseCase-$28`

#### 测试步骤模板

**A. 不支持的会话 SPRMIB**
```
1. 进入 Default 会话
2. Send DiagBy[Physical]Data[28 <0x80+Sub> <CommType>];
（可合并多个组合在同一用例中）
```

**B. 不支持的 SPRMIB 子功能**
```
1. 进入 Extended 会话
2. Send DiagBy[Physical]Data[28 <0x80+UnsupportedSub> <CommType>];
（可合并多个 CommType 在同一用例中）
```

**C. 支持的 SPRMIB**
```
1. 进入 Extended 会话
2. Send DiagBy[Physical]Data[28 <0x80+Sub> <CommType>];
```

#### Check 规则

**A. 不支持的会话：**
- `Check DiagData[7F 28 7F]Within[50]ms;`

**B. 不支持的 SPRMIB 子功能：**
- `Check DiagData[7F 28 12]Within[50]ms;`

**C. 支持的 SPRMIB：**
- `Check No_Response Within[1000]ms;`

---

### 分类 4: Communication Control Function Test (APP)

#### 用例数量规则

- 禁用→验证→恢复 的完整功能测试
- 覆盖正常子功能和 SPRMIB 版本
- **固定 ~4 条**

#### 用例命名规则

`0x28 Service control <CommTypeDesc> function test PositiveResponseCase-$28`

#### 测试步骤模板

**A. 正常子功能禁用→恢复（01/NormalMsg）**
```
1. 进入 Extended 会话
2. Send DiagBy[Physical]Data[28 03 01];
3. Check MsgInexist[<MonitoredMsgId>];
4. Send DiagBy[Physical]Data[28 00 01];
5. Check MsgExist[<MonitoredMsgId>];
```

**B. 正常子功能禁用→恢复（03/Both）**
```
1. 进入 Extended 会话
2. Send DiagBy[Physical]Data[28 03 03];
3. Check MsgInexist[<MonitoredMsgId>];
4. Send DiagBy[Physical]Data[28 00 03];
5. Check MsgExist[<MonitoredMsgId>];
```

**C. SPRMIB 版本禁用→恢复（83/NormalMsg）**
```
1. 进入 Extended 会话
2. Send DiagBy[Physical]Data[28 83 01];
3. Check MsgInexist[<MonitoredMsgId>];
4. Send DiagBy[Physical]Data[28 80 01];
5. Check MsgExist[<MonitoredMsgId>];
```

**D. SPRMIB 版本禁用→恢复（83/Both）**
```
1. 进入 Extended 会话
2. Send DiagBy[Physical]Data[28 83 03];
3. Check MsgInexist[<MonitoredMsgId>];
4. Send DiagBy[Physical]Data[28 80 03];
5. Check MsgExist[<MonitoredMsgId>];
```

#### Check 规则

- 禁用正响应：`Check DiagData[68 03]Within[50]ms;` + `Check MsgInexist[<MsgId>];`
- SPRMIB 禁用：`Check No_Response Within[1000]ms;` + `Check MsgInexist[<MsgId>];`
- 恢复正响应：`Check DiagData[68 00]Within[50]ms;` + `Check MsgExist[<MsgId>];`
- SPRMIB 恢复：`Check No_Response Within[1000]ms;` + `Check MsgExist[<MsgId>];`

---

### 分类 5: ECU Reset Test (APP)

#### 用例数量规则

| 复位方式 | 数量 |
|---------|------|
| Session Switch（10 01） | 1（可包含多次禁用→恢复） |
| S3 超时 | 1 |
| Hardware Reset(11 01) | 1 |
| Power Reset | 1 |
| **小计** | **4 条** |

#### 用例命名规则

`<ResetType> reset 0x28 service <CommTypeDesc> control state NegativeCase-$28`

#### 测试步骤模板

**A. Session Switch（10 01）：**
```
1. 进入 Extended 会话
2. Send DiagBy[Physical]Data[28 03 01];
3. Check MsgInexist[<MonitoredMsgId>];
4. Send DiagBy[Physical]Data[10 01];
5. Check MsgExist[<MonitoredMsgId>];
（可重复 28 03 03 → 10 01 验证）
```

**B. S3 超时：**
```
1. 进入 Extended 会话
2. Send DiagBy[Physical]Data[28 03 01];
3. Check MsgInexist[<MonitoredMsgId>];
4. Send DiagBy[Physical]Data[3E 00];
5. Delay[5100]ms;
6. Check MsgExist[<MonitoredMsgId>];
```

**C. Hardware Reset(11 01)：**
```
1. 进入 Extended 会话
2. Send DiagBy[Physical]Data[28 03 01];
3. Check MsgInexist[<MonitoredMsgId>];
4. Send DiagBy[Physical]Data[11 01];
5. Delay[2000]ms;
6. Check MsgExist[<MonitoredMsgId>];
```

**D. Power Reset：**
```
1. 进入 Extended 会话
2. Send DiagBy[Physical]Data[28 03 01];
3. Check MsgInexist[<MonitoredMsgId>];
4. Set Voltage[0]V;
5. Delay[1000]ms;
6. Set Voltage[12]V;
7. Delay[1000]ms;
8. Check MsgExist[<MonitoredMsgId>];
```

#### Check 规则

- 第 2 步：`Check DiagData[68 03]Within[50]ms;` + `Check MsgInexist[<MsgId>];`
- 复位后：`Check MsgExist[<MsgId>];`（确认报文恢复发送）

---

### 分类 6: Sub-function Traversal And Network Type Test (APP)

#### 用例数量规则

**固定 4 条**

| 类型 | 数量 | 描述 |
|------|------|------|
| 子功能遍历 × commType 01 | 1 | With Parameter[0x01] |
| 子功能遍历 × commType 03 | 1 | With Parameter[0x03] |
| communicationType 遍历 × Sub 0x00 | 1 | With Sub[0x00] |
| communicationType 遍历 × Sub 0x03 | 1 | With Sub[0x03] |

#### 用例命名规则

- `Subfunction traversal test control <CommTypeDesc> NegativeCase-$28`
- `Network type parameter traversal test 0x28 Service 0x<Sub> subfunction NegativeCase-$28`

#### 测试步骤模板

**A. 子功能遍历：**
```
1. 进入 Extended 会话
2. Send 0x28SubTraversalBy[Physical]Excluding[<SupportSubList>]With Parameter[<CommType>]AndCheckResp[0x12];
```

**B. communicationType 遍历：**
```
1. 进入 Extended 会话
2. Send 0x28ParameterTraversalBy[Physical]With Sub[<Sub>]Excluding[<SupportCommTypeList>]AndCheckResp[0x31];
```

#### Check 规则

- 第 A2 步：不支持的子功能 → `7F 28 12`
- 第 B2 步：不支持的 communicationType → `7F 28 31`

#### 特殊规则

1. Excluding 列表包含所有支持的子功能（含 SPRMIB 版本如 80 83）
2. communicationType 遍历使用 `0x28ParameterTraversalBy` 特殊函数
3. 子功能遍历使用 `With Parameter[<CommType>]` 限定 communicationType

---

### 分类 7: Incorrect Diagnostic Command Test (APP)

#### 用例数量规则

**固定 2 条**

| 序号 | 错误类型 | 描述 |
|------|---------|------|
| 1 | SF_DL > 3 | 有效负载长度大于合法值 |
| 2 | SF_DL < 3 | 有效负载长度小于合法值 |

#### 用例命名规则

1. `Valid SF_DL=3, invalid SF_DL < 3, and those with invalid equivalence class SF_DL=2 NegativeCase-$28`
2. `Valid SF_DL=3, invalid SF_DL > 3, and those with invalid equivalence class SF_DL=4 NegativeCase-$28`

#### 测试步骤模板

**前置步骤：** 进入支持 0x28 的当前会话（Extended）

**A. SF_DL > 3**
```
Send DiagBy[Physical]Data[28 03 01]WithLen[4];
```

**B. SF_DL < 3**
```
Send DiagBy[Physical]Data[28 03 01]WithLen[2];
```

#### Check 规则

| 错误类型 | Expected Output |
|---------|----------------|
| SF_DL > 3 | `Check DiagData[7F 28 13]Within[50]ms;` |
| SF_DL < 3 | `Check DiagData[7F 28 13]Within[50]ms;` |

#### 特殊规则

1. 0x28 的合法 SF_DL 为 3 字节（SID + Sub + communicationType）
2. **不生成 DLC 测试用例**（DLC < 8 / DLC > 8）
3. SF_DL 错误使用 `Send DiagBy...WithLen[...]`

---

### 分类 8: NRC Priority Test (APP)

#### 用例数量规则

**固定 1 条**

#### 用例命名规则

`NRC 13>12 NegativeCase-$28`

#### 测试步骤

```
1. 进入 Extended 会话
2. Send Msg[<ReqCANID>]Data[<FormattedMessageWithInvalidDLC>]WithDLC[8];
```

其中：发送一个同时触发 NRC 0x13（长度错误）和 NRC 0x12（子功能不支持）的报文，验证 ECU 优先返回 NRC 0x13。

示例：
```
1. Send DiagBy[Physical]Data[10 03];
2. Send Msg[0x3C]Data[0B 02 28 02 01 FF FF FF]WithDLC[8];
```

#### Check 规则

```
1. Check DiagData[50 03 00 32 01 F4]Within[50]ms;
2. Check DiagData[7F 28 13]Within[50]ms;
```

---

### 分类 9: Functional Addressing Test

#### 用例数量规则

**Functional 用例集是 Physical APP 用例集的完整镜像**
- 将所有 Physical APP 用例（分类 1-8）复制一份
- 所有发送函数中 `[Physical]` 改为 `[Function]`
- 所有预期输出改为 `Check No_Response Within[1000]ms;`
- Case ID 中 `Phy` 改为 `Fun`，编号重新从 001 开始
- 安全访问步骤（0x27 seed/key）仍使用 `[Physical]`

#### 额外用例

在完整镜像之外，还需追加以下额外用例：

1. **Physical 寻址验证 NRC**（1 条）：在 Default 会话下使用 Physical 寻址发送所有子功能，验证均返回 `7F 28 7F`
2. **DLC 测试**（可选，如参数表要求）：
   - DLC < 8 → `Check No_Response Within[1000]ms;`
   - DLC > 8 → 正常响应或 No_Response
3. **SF_DL 测试**（2 条）：使用 `[Function]` 发送 SF_DL 错误的报文 → `Check No_Response Within[1000]ms;`

#### Check 规则

- 所有 Functional 发送的测试步骤：`Check No_Response Within[1000]ms;`
- 安全访问仍使用 Physical：`Check DiagData[67 <KeySub>]Within[50]ms;`
- MsgInexist/MsgExist 验证仍保留

---

## 会话进入标准路径

为统一生成，进入各会话的标准路径如下：

| 目标会话 | 标准进入步骤 |
|---------|------------|
| Default（0x01） | `Send DiagBy[Physical]Data[10 01];` |
| Extended（0x03） | `Send DiagBy[Physical]Data[10 01];` → `Delay[1000]ms;` → `Send DiagBy[Physical]Data[10 03];` |
| Programming（0x02） | `Send DiagBy[Physical]Data[10 01];` → `Delay[1000]ms;` → `Send DiagBy[Physical]Data[10 03];` → `Send DiagBy[Physical]Data[31 01 02 03];` → `Send DiagBy[Physical]Data[10 02];` |

注意：Programming Session 进入路径使用 `31 01 02 03`（RoutineControl StartRoutine），不是直接 `10 02`。

---

## 生成注意事项

1. **Case ID 不可重复**，物理寻址 `Diag_0x28_Phy_001` 起递增，功能寻址 `Diag_0x28_Fun_001` 起递增
2. **编号从 001 开始**，优先编写所有 Physical 用例，再编写 Functional 用例
3. **每个 Send 都要有对应 Check**，除以下豁免：
   - `Delay[...]ms` 不写 Check
   - 带 `AndCheckResp[...]` 的发送函数不单独写 Check
4. **禁用后必须验证 MsgInexist**，恢复后必须验证 MsgExist
5. **被控报文 ID 从参数表读取**（MonitoredMsgId，如 0x1B），不写死
6. **输出格式严格按照 Case ID / Case名称 / 测试步骤 / 预期输出 的固定模板**

---

## 分类汇总

| 分类 | 描述 | 用例数量公式 |
|------|------|-------------|
| 1. Session Layer (APP) | 每个会话 × 子功能 × commType 组合 | `~8 条` |
| 2. Secure Access (APP) | L1 解锁 × sub×commType 组合 | `~5 条` |
| 3. SPRMIB (APP) | 每个会话 × SPRMIB子功能 × commType | `~9 条` |
| 4. Comm Control Function (APP) | 禁用→验证→恢复 | `~4 条` |
| 5. ECU Reset (APP) | 4种复位方式 | `~4 条` |
| 6. Sub-function Traversal (APP) | 子功能遍历 + commType遍历 | `~4 条` |
| 7. Incorrect Command (APP) | SF_DL 错误 | `固定 2 条` |
| 8. NRC Priority (APP) | NRC 优先级 | `固定 1 条` |
| 9. Functional Addressing | Physical 完整镜像(No_Response) + 额外用例 | `~37+条` |
