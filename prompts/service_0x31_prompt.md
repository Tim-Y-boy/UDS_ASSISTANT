# Service 0x31 RoutineControl — 用例生成规则

## 服务概述

- **Service ID**: 0x31
- **Service Name**: RoutineControl
- **正响应 SID**: 0x71（0x31 + 0x40）
- **负响应格式**: `7F 31 <NRC>`
- **子功能**: 01(StartRoutine), 02(StopRoutine), 03(RequestRoutineResults)
- **请求格式**: `31 <Sub> <RID_H> <RID_L> [+ Routine Option 数据]`
- **合法 SF_DL**: 4 + Option 数据长度（最小 4：SID + Sub + RID 2 字节）
- **关键特性**: 每个 RID + 每个 Subfunction 组合原则上各一条用例；正响应含 StatusByte

### 正响应格式

- `71 <Sub> <RID_H> <RID_L> [+ Routine Status / Response 数据]`
- StatusByte 解读需从 RID 的 Response 参数定义中读取
  - 如 CheckProgrammingPreCondition: 0x00=正常, 0x01=异常
  - 如 DimmingControl: 0x00=correct, 0x01=incorrect

### 典型 NRC

| NRC  | 含义 | 触发条件 |
|------|------|---------|
| 0x12 | Subfunction Not Supported | 发送了不支持的子功能 |
| 0x13 | Incorrect Message Length Or Invalid Format | 报文长度错误 |
| 0x22 | Conditions Not Correct | 前置条件不满足（如电压异常） |
| 0x24 | RequestSequenceError | 序列错误 |
| 0x31 | Request Out Of Range | RID 不支持或不存在 |
| 0x33 | Security Access Denied | 需要安全解锁但未解锁 |
| 0x7E | Subfunction Not Supported In Active Session | 该子功能在当前会话下不支持 |
| 0x7F | Service Not Supported In Active Session | 当前会话下不支持 0x31 服务 |

---

## 生成分类（共 5 类）

按以下固定顺序逐类生成，每个分类使用 `## N.N` 作为标题（如 `## 1.1 Session Layer Test`）。

---

### 分类 1: Session Layer Test

#### 用例数量规则

- `Npos` = 支持的 RID × 支持的 Subfunction × 支持的会话数
- `Nneg_sf` = 不支持的子功能 case 数
- `Nneg_sess` = 不支持的会话 case 数
- **总数 = Npos + Nneg_sf + Nneg_sess**

#### 用例命名规则

- 正向：`<CurrentSessionName> Session support the 0x31 service 0x<Sub> subfunction RID 0x<RID>`
  - 示例：`Extended Session support the 0x31 service 0x01 subfunction RID 0x0200`
- 负向（会话不支持）：`<CurrentSessionName> Session nonsupport 0x31 services`
- 负向（子功能不支持）：`0x31 service RID 0x<RID> nonsupport 0x<Sub> subfunction`

#### 测试步骤模板

**A. 不支持的会话（如 Default）**
```
1. 进入 Default 会话
2. Send DiagBy[Physical]Data[31 <Sub> <RID_H> <RID_L>];
```

**B. 支持会话正向（StartRoutine）**
```
1. 进入支持的会话（通常 Extended）
2. Send DiagBy[Physical]Data[31 01 <RID_H> <RID_L> <OptionData>];
```

**C. 支持会话正向（StopRoutine / RequestRoutineResults）**
```
1. 进入支持的会话
2. Send DiagBy[Physical]Data[31 <Sub> <RID_H> <RID_L>];
```

**D. 子功能不支持**
```
1. 进入支持的会话
2. Send DiagBy[Physical]Data[31 <UnsupportedSub> <RID_H> <RID_L>];
```

#### Check 规则

**A. 不支持的会话：**
- `Check DiagData[7F 31 7F]Within[50]ms;`

**B. 支持会话正向（StartRoutine）：**
- `Check DiagData[71 01 <RID_H> <RID_L> <StatusByte>]Within[50]ms;`
- StatusByte 含义从 RID 定义读取

**C. 支持会话正向（Stop/Results）：**
- `Check DiagData[71 <Sub> <RID_H> <RID_L> [<ResponseData>]]Within[50]ms;`

**D. 子功能不支持：**
- `Check DiagData[7F 31 12]Within[50]ms;`

#### 特殊规则

1. 每个 RID + 每个 Subfunction 组合原则上各一条用例
2. StartRoutine(01) 可能需要附带 Option 数据（如 DimmingControl 的 Level 值）
3. StopRoutine(02) 和 RequestRoutineResults(03) 通常无附加数据
4. OptionData 从 RID 定义表的 Request 参数读取
5. StatusByte 含义从 RID 定义表的 Response 参数读取

---

### 分类 2: Secure Access Test

#### 用例数量规则

- 从参数表 RID 的 `Access Level` 字段读取安全等级
- 仅对需要安全解锁的 RID 生成
- **总数 = N_rid_need_security**

#### 用例命名规则

`Security access Lx unlock supports 0x31 service 0x<Sub> subfunction RID 0x<RID>`
- 示例：`Security access L2 unlock supports 0x31 service 0x01 subfunction RID 0x0200`

#### 测试步骤模板

```
1. 进入支持的会话（通常 Extended）
2. Send DiagBy[Physical]Data[27 <SeedSub>]AndCheckResp[PostiveResponse];
3. Send Security Right KeyBy[Physical]Level[<KeySub>];
4. Send DiagBy[Physical]Data[31 <Sub> <RID_H> <RID_L> <OptionData>];
```

#### Check 规则

- 第 3 步：`Check DiagData[67 <KeySub>]Within[50]ms;`
- 第 4 步：`Check DiagData[71 <Sub> <RID_H> <RID_L> <StatusByte>]Within[50]ms;`

---

### 分类 3: Routine Condition Test

#### 用例数量规则

- 仅对有 Routine Condition 或需要特定前置条件的 RID 生成
- 典型场景：

| 场景 | 数量 |
|------|------|
| 电压条件测试 | 2（异常 + 恢复） |
| 编程前置条件测试 | 2（正常 + 异常） |
| 其他条件 | 按条件数 |

#### 用例命名规则

- `RID 0x<RID> routine condition test with <Condition>`
- 示例：`RID 0x0203 CheckProgrammingPreCondition with normal voltage`
- 示例：`RID 0x0203 CheckProgrammingPreCondition with abnormal voltage`

#### 测试步骤模板

**A. 电压条件测试：**
```
1. 进入 Extended 会话
2. 完成安全解锁（若需要）
3. Set Voltage[8.5]V;（异常电压）
4. Delay[1000]ms;
5. Send DiagBy[Physical]Data[31 01 <RID_H> <RID_L>];
6. Set Voltage[12]V;（恢复正常电压）
7. Delay[1000]ms;
8. Send DiagBy[Physical]Data[31 01 <RID_H> <RID_L>];
```

**B. 编程前置条件测试：**
```
1. 进入 Extended 会话
2. 完成安全解锁（若需要）
3. （正常条件下）Send DiagBy[Physical]Data[31 01 <RID_H> <RID_L>];
4. （破坏条件）Send DiagBy[Physical]Data[31 01 <RID_H> <RID_L>];
```

#### Check 规则

**A. 电压条件：**
- 异常电压（第 5 步）：`Check DiagData[71 01 <RID> 01]Within[50]ms;`（status=异常）
- 正常电压（第 8 步）：`Check DiagData[71 01 <RID> 00]Within[50]ms;`（status=正常）

**B. 编程前置条件：**
- 条件满足：`Check DiagData[71 01 <RID> 00]Within[50]ms;`
- 条件不满足：`Check DiagData[71 01 <RID> 01]Within[50]ms;` 或 `Check DiagData[7F 31 22]Within[50]ms;`

#### 特殊规则

1. 异常电压值从 RID 定义的条件读取（典型：8.5V 欠压 或 16.5V 过压）
2. StatusByte 0x00=条件满足/正常, 0x01=条件不满足/异常
3. 编程前置条件 RID（如 CheckProgrammingPreCondition）必须有此测试

---

### 分类 4: Sub-function Traversal And RID Range Test

#### 用例数量规则

**固定 2 条**（子功能遍历 1 + RID 遍历 1）

#### 用例命名规则

- `Subfunction traversal test for 0x31 service RID 0x<RID>`
- `RID range traversal test for 0x31 service`

#### 测试步骤模板

**A. 子功能遍历：**
```
1. 进入 Extended 会话
2. Send SubTraversalBy[Physical]Service[0x31]Excluding[<SupportSubList>]AndCheckResp[0x12];
```
- Excluding 包括支持的子功能 + SPRMIB 镜像

**B. RID 遍历：**
```
1. 进入 Extended 会话
2. Send DIDTraversalBy[Physical]Service[0x31]Excluding[<SupportRIDList>]AndCheckResp[0x31];
```
- Excluding 包括所有支持的 RID

#### Check 规则

- 不支持的子功能 → `7F 31 12`
- 不支持的 RID → `7F 31 31`

---

### 分类 5: Incorrect Diagnostic Command Test

#### 用例数量规则

**固定 4 条**

| 序号 | 错误类型 | 描述 |
|------|---------|------|
| 1 | DLC < 8 | CAN 帧 DLC 不足 8 字节 |
| 2 | DLC > 8 | CAN 帧 DLC 超过 8 字节 |
| 3 | SF_DL > 合法值 | 有效负载长度大于合法值 |
| 4 | SF_DL < 合法值 | 有效负载长度小于合法值 |

注意：0x31 的合法 SF_DL 最小为 4（SID + Sub + RID 2 字节），含 Option 数据时更长。

#### 用例命名规则

1. `When a diagnostic message with DLC < 8 is sent, ECU does not respond`
2. `When a diagnostic message with DLC > 8 is sent, ECU responds normally`
3. `Valid SF_DL=<legal>, invalid SF_DL > <legal> triggers NRC 0x13`
4. `Valid SF_DL=<legal>, invalid SF_DL < <legal> triggers NRC 0x13`

#### 测试步骤模板

选择一个代表性 RID 进行测试。

**前置步骤：** 进入支持 0x31 的当前会话（通常 Extended）

**A. DLC < 8**
```
Send Msg[<ReqCANID>]Data[04 31 01 <RID_H> <RID_L>]WithDLC[7];
```

**B. DLC > 8**
```
Send Msg[<ReqCANID>]Data[04 31 01 <RID_H> <RID_L>]WithDLC[9];
```

**C. SF_DL > 合法值**
```
Send DiagBy[Physical]Data[31 01 <RID_H> <RID_L>]WithLen[5];
```

**D. SF_DL < 合法值**
```
Send DiagBy[Physical]Data[31 01 <RID_H>]WithLen[3];
```

#### Check 规则

| 错误类型 | Expected Output |
|---------|----------------|
| DLC < 8 | `Check No_Response Within[1000]ms;` |
| DLC > 8 | `Check DiagData[71 01 <RID> <Status>]Within[50]ms;` |
| SF_DL 异常 | `Check DiagData[7F 31 13]Within[50]ms;` |

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

当 `Functional Request = 不支持` 时（0x31 典型情况）：
- 仅生成 1 条 No_Response 验证用例

---

## 生成注意事项

1. **Case ID 不可重复**，物理寻址 `Diag_0x31_Phy_001` 起递增
2. **每个 Send 都要有对应 Check**
3. **RID 列表从 Routine Control 表（Sheet 含 "Routine"/"0x31"）读取**
4. **每个 RID + 每个 Subfunction 组合各一条用例**（除非不支持）
5. **OptionData 从 RID 的 Request 参数定义读取**，StartRoutine 通常需要
6. **StatusByte 含义从 RID 的 Response 参数定义读取**
7. **有前置条件的 RID 必须生成 Condition Test**
8. **输出格式严格为 pipe table**，列顺序：`| Case ID | Case名称 | 测试步骤 | 预期输出 |`
9. **顶级标题使用 `#`**：如 `# 1. Application Service_Physical Addressing`、`# 2. Application Service_Functional Addressing` 等
10. **分类标题使用 `##`**：如 `## 1.1 Session Layer Test` 等
11. **各大组之间用 `---` 分隔**
12. **无符合条件的用例时使用 `>` 引用**
13. **步骤中换行使用 `<br>` 标记**，不用 `\n`
