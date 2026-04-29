# Service 0x14 ClearDiagnosticInformation — 用例生成规则

## 服务概述

- **Service ID**: 0x14
- **Service Name**: ClearDiagnosticInformation
- **正响应 SID**: 0x54（0x14 + 0x40）
- **负响应格式**: `7F 14 <NRC>`
- **请求格式**: `14 FF FF FF`（清除所有 DTC 组）
- **合法 SF_DL**: 4 字节（SID + 3 字节 groupOfDTC）
- **关键特性**: 清除 DTC 后需用 0x19 验证清除效果；清除前需先确认有 DTC 可清

### 正响应格式

- `54`（无额外 payload，仅 SID 确认）

### 典型 NRC

| NRC  | 含义 | 触发条件 |
|------|------|---------|
| 0x13 | Incorrect Message Length Or Invalid Format | 报文长度错误（SF_DL ≠ 4） |
| 0x22 | Conditions Not Correct | 前置条件不满足 |
| 0x31 | Request Out Of Range | groupOfDTC 值不支持 |
| 0x7F | Service Not Supported In Active Session | 当前会话下不支持 0x14 服务 |

---

## 生成分类（共 5 类）

按以下固定顺序逐类生成，每个分类之间用 `--service ID 0x14 <分类名>` 分隔。

---

### 分类 1: Session Layer Test

#### 用例数量规则

- `Npos` = 支持的会话正向 case 数（每个支持 0x14 的会话 1 条）
- `Nneg_sess` = 不支持的会话负向 case 数（每个不支持 0x14 的会话 1 条）
- **总数 = Npos + Nneg_sess**

#### 用例命名规则

- 正向：`<CurrentSessionName> Session support the 0x14 service`
  - 示例：`Extended Session support the 0x14 service`
- 负向（会话不支持）：`<CurrentSessionName> Session nonsupport 0x14 services`
  - 示例：`Default Session nonsupport 0x14 services`

#### 测试步骤模板

**A. 当前会话不支持 0x14 服务（负向）**
```
1. 进入 <CurrentSessionNotSupport>（通常为 Default）
2. Send DiagBy[Physical]Data[14 FF FF FF];
```

**B. 支持会话正向**
```
1. 进入 <CurrentSessionSupport>（通常为 Extended）
2. Stop MsgCycle[<FaultMsgId>];
3. Delay[3000]ms;
4. Send DiagBy[Physical]Data[19 02 FF];
5. Send DiagBy[Physical]Data[14 FF FF FF];
6. Send DiagBy[Physical]Data[19 02 FF];
7. Send MsgCycle[<FaultMsgId>];
```

其中：
- `<FaultMsgId>` 从 DTC 表读取，选择一个可触发 DTC 的故障报文 ID
- 步骤 2-4 为前置故障制造，先确认有 DTC 可清
- 步骤 7 为后置恢复，重新启动报文周期

#### Check 规则

**A. 当前会话不支持服务：**
- `Check DiagData[7F 14 7F]Within[50]ms;`

**B. 支持会话正向：**
- 第 4 步：`Check DiagData[59 02 <AvailabilityMask> <DTC_3bytes> <Status>]Within[50]ms;`（验证 DTC 存在）
- 第 5 步：`Check DiagData[54]Within[50]ms;`（清除成功）
- 第 6 步：`Check DiagData[59 02 FF 00 00]Within[50]ms;`（验证 DTC 已清除，无 DTC 数据返回）

#### 特殊规则

1. 清除前必须先制造故障并验证 DTC 存在，否则无法验证清除效果
2. DTC 状态位定义需从 DTC Status Definition 表读取（本项目仅 bit0 和 bit3 支持，mask=0x09）
3. `19 02 FF` 返回无 DTC 时格式为 `59 02 FF 00 00`（AvailabilityMask + NumberOfDTC=0）
4. 故障制造方法从 DTC 表读取（典型：Stop MsgCycle 停止周期报文）

---

### 分类 2: Secure Access Test

#### 用例数量规则

- 从参数表 `Access Level` 字段读取安全等级
- 若 0x14 无安全限制，则不生成本类 case
- **总数 = Nsecure14**

#### 用例命名规则

`Security access Lx unlock supports 0x14 service`
- 示例：`Security access L2 unlock supports 0x14 service`

#### 测试步骤模板

```
1. 进入允许安全访问的会话（通常 Extended）
2. Stop MsgCycle[<FaultMsgId>];
3. Delay[3000]ms;
4. Send DiagBy[Physical]Data[19 02 FF];
5. Send DiagBy[Physical]Data[27 <SeedSub>]AndCheckResp[PostiveResponse];
6. Send Security Right KeyBy[Physical]Level[<KeySub>];
7. Send DiagBy[Physical]Data[14 FF FF FF];
8. Send DiagBy[Physical]Data[19 02 FF];
9. Send MsgCycle[<FaultMsgId>];
```

#### Check 规则

- 第 4 步：验证 DTC 存在
- 第 6 步：`Check DiagData[67 <KeySub>]Within[50]ms;`
- 第 7 步：`Check DiagData[54]Within[50]ms;`
- 第 8 步：验证 DTC 已清除

#### 特殊规则

1. 安全等级不写死，必须从参数表所在软件域的 Access Level 读取
2. SeedSub/KeySub 对应关系：L1 → 27 01/27 02，L2 → 27 03/27 04，L3 → 27 05/27 06，L4 → 27 07/27 08，L5 → 27 09/27 0A

---

### 分类 3: Clear DTC Function Test

#### 用例数量规则

固定 5 条，覆盖以下场景：

| 序号 | 场景 | 描述 |
|------|------|------|
| 1 | 清除单个 DTC（状态 09） | testFailed + confirmedDTC |
| 2 | 清除单个 DTC（状态 08） | 仅 confirmedDTC |
| 3 | 清除多个 DTC | 制造多个故障后一次清除 |
| 4 | 无 DTC 时清除 | 验证正响应但无实际效果 |
| 5 | 清除后重新触发 | 验证 DTC 可重新记录 |

#### 用例命名规则

1. `Clear single DTC with status 0x09`
2. `Clear single DTC with status 0x08`
3. `Clear multiple DTCs at once`
4. `Clear DTC when no DTC exists`
5. `Re-trigger fault after DTC cleared`

#### 测试步骤模板

**场景 1: 清除单个 DTC（状态 09）**
```
1. 进入支持的会话（Extended）
2. Stop MsgCycle[<FaultMsgId>];
3. Delay[3000]ms;
4. Send DiagBy[Physical]Data[19 02 FF];
5. Send DiagBy[Physical]Data[14 FF FF FF];
6. Send DiagBy[Physical]Data[19 02 FF];
7. Send MsgCycle[<FaultMsgId>];
```

**场景 4: 无 DTC 时清除**
```
1. 进入支持的会话（Extended）
2. Send DiagBy[Physical]Data[14 FF FF FF];
3. Send DiagBy[Physical]Data[19 02 FF];
```

**场景 5: 清除后重新触发**
```
1. 进入支持的会话（Extended）
2. Stop MsgCycle[<FaultMsgId>];
3. Delay[3000]ms;
4. Send DiagBy[Physical]Data[19 02 FF];
5. Send DiagBy[Physical]Data[14 FF FF FF];
6. Send DiagBy[Physical]Data[19 02 FF];
7. Send MsgCycle[<FaultMsgId>];
8. Stop MsgCycle[<FaultMsgId>];
9. Delay[3000]ms;
10. Send DiagBy[Physical]Data[19 02 FF];
```

#### Check 规则

- 清除成功：`Check DiagData[54]Within[50]ms;`
- DTC 存在验证：`Check DiagData[59 02 <Mask> <DTC> <Status>]Within[50]ms;`
- DTC 已清除验证：`Check DiagData[59 02 FF 00 00]Within[50]ms;`
- 场景 5 第 10 步：验证 DTC 可重新记录（`59 02` 返回含 DTC 数据）

#### 特殊规则

1. 每个 DTC 的触发条件不同，需从 DTC 表读取对应方法
2. 多 DTC 场景需选择不同的故障报文分别触发
3. 场景 5 是完整性验证：清除后系统仍能正常记录新的 DTC

---

### 分类 4: Incorrect Diagnostic Command Test

#### 用例数量规则

**固定 4 条**

| 序号 | 错误类型 | 描述 |
|------|---------|------|
| 1 | DLC < 8 | CAN 帧 DLC 不足 8 字节 |
| 2 | DLC > 8 | CAN 帧 DLC 超过 8 字节 |
| 3 | SF_DL > 4 | 有效负载长度大于合法值 |
| 4 | SF_DL < 4 | 有效负载长度小于合法值 |

#### 用例命名规则

1. `When a diagnostic message with DLC < 8 is sent, ECU does not respond`
2. `When a diagnostic message with DLC > 8 is sent, ECU responds normally`
3. `Valid SF_DL=4, invalid SF_DL > 4 triggers NRC 0x13`
4. `Valid SF_DL=4, invalid SF_DL < 4 triggers NRC 0x13`

#### 测试步骤模板

**前置步骤（所有 4 条共用）：**
进入支持 0x14 的当前会话（通常 Extended）

**A. DLC < 8**
```
Send Msg[<ReqCANID>]Data[04 14 FF FF FF]WithDLC[7];
```

**B. DLC > 8**
```
Send Msg[<ReqCANID>]Data[04 14 FF FF FF]WithDLC[9];
```

**C. SF_DL > 4**
```
Send DiagBy[Physical]Data[14 FF FF FF]WithLen[5];
```

**D. SF_DL < 4**
```
Send DiagBy[Physical]Data[14 FF FF FF]WithLen[3];
```

#### Check 规则

| 错误类型 | Expected Output |
|---------|----------------|
| DLC < 8 | `Check No_Response Within[1000]ms;` |
| DLC > 8 | `Check DiagData[54]Within[50]ms;` |
| SF_DL > 4 | `Check DiagData[7F 14 13]Within[50]ms;` |
| SF_DL < 4 | `Check DiagData[7F 14 13]Within[50]ms;` |

#### 特殊规则

1. 0x14 的合法 SF_DL 为 4 字节（SID + 3 字节 groupOfDTC），不同于 0x10/0x11 的 2 字节
2. DLC 错误测试使用 `Send Msg...WithDLC[...]`
3. SF_DL 错误测试使用 `Send DiagBy...WithLen[...]`

---

### 分类 5: Functional Addressing Test

#### 用例数量规则

**仅当参数表 `Functional Request = 不支持` 时生成，固定 1 条。**

若 `Functional Request = 支持`，则不使用本分类，改为复制 Session/Secure/Incorrect 的 Functional 版本。

#### 用例命名规则

`0x14 Service nonsupport functional addressing`

#### 测试步骤模板

```
1. 进入 Extended 会话（使用 Physical）
2. Send DiagBy[Function]Data[14 FF FF FF];
```

#### Check 规则

- 第 2 步：`Check No_Response Within[1000]ms;`

#### 特殊规则

1. 0x14 通常不支持功能寻址
2. 若项目支持功能寻址，则复制分类 1-4 的物理寻址用例，改 Send 为 Function

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

当 `Functional Request = 支持` 时：
1. 将所有 Physical 用例复制一份
2. 发送函数中 `[Physical]` 改为 `[Function]`
3. Case ID 中 `Phy` 改为 `Fun`，编号重新从 001 开始
4. 安全访问步骤（0x27 seed/key）仍使用 Physical

当 `Functional Request = 不支持` 时：
- 仅生成分类 5 的 No_Response 验证用例

---

## 生成注意事项

1. **Case ID 不可重复**，物理寻址 `Diag_0x14_Phy_001` 起递增，功能寻址 `Diag_0x14_Fun_001` 起递增
2. **编号从 001 开始**，优先编写所有 Physical 用例，再编写 Functional 用例
3. **每个 Send 都要有对应 Check**，除以下豁免：
   - `Delay[...]ms` 不写 Check
   - 带 `AndCheckResp[...]` 的发送函数不单独写 Check
4. **DTC 验证必须成对出现**：清除前验证存在 + 清除后验证已清除
5. **故障制造方法从 DTC 表读取**，不同 DTC 的触发条件不同
6. **输出格式严格按照 Case ID / Case名称 / 测试步骤 / 预期输出 的固定模板**
