# Service 0x22 ReadDataByIdentifier — 用例生成规则

<!--
## 版本管控

| 版本 | 日期 | 变更说明 |
|------|------|---------|
| v1.0 | — | 初始版本 |
| v1.1 | 2026-05-06 | 1) APP不支持会话NRC从0x7F修正为0x31；2) Secure Access即使Level0也必须生成；3) 新增Unsupported DID测试规则；4) Boot功能寻址完整覆盖；5) DID Range/Incorrect Command/NRC Priority多会话覆盖 |
| v1.2 | 2026-05-06 | 基于奇瑞/华智/蔚来/恒润四方对比优化：1) 新增核心原则宁滥勿缺+精准度；2) Functional=Y时完整镜像；3) 新增CAN DLC测试；4) Delay可选；5) Fun连续编号；6) 混合寻址安全访问；7) 数据填充优先用精确值 |
-->

## 核心原则

1. **宁滥勿缺**：用例覆盖率优先，宁可多生成不可漏生成。所有分类、会话、DID组合都必须覆盖完整，不可为简化而减少用例数量
2. **精准度要求**：预期输出中的参数必须精确——从参数表中提取 DefaultValue、Byte Length、数据类型等信息填充实际值，尽量避免使用 xx 占位符。只有参数表确实未定义且无法推断的值才使用 xx

## 服务概述

- **Service ID**: 0x22
- **Service Name**: ReadDataByIdentifier
- **正响应 SID**: 0x62（0x22 + 0x40）
- **负响应格式**: `7F 22 <NRC>`
- **请求格式**: `22 <DID_H> <DID_L>`
- **无 Subfunction**（DID 替代子功能角色）
- **合法 SF_DL**: 3 字节（SID + DID 2 字节）
- **关键特性**: 不存在 NRC 0x12（因为没有子功能概念）；NRC 0x31 用于不支持的 DID

### 正响应格式

- `62 <DID_H> <DID_L> <Data...>`
- 数据长度 = DID 的 Byte Length（从 DID 表读取）
- 数据内容使用 DefaultValue（如参数表有定义）或 xx 占位

### 典型 NRC

| NRC  | 含义 | 触发条件 |
|------|------|---------|
| 0x13 | Incorrect Message Length Or Invalid Format | 报文长度错误（SF_DL ≠ 3） |
| 0x31 | Request Out Of Range | DID 不支持或不在有效范围 |
| 0x33 | Security Access Denied | 需要安全解锁但未解锁 |
| 0x7F | Service Not Supported In Active Session | 当前会话下不支持 0x22 服务 |

---

## 软件域规则

- **必须为 APP 和 Boot 两个软件域各独立生成完整用例集**
- APP 域使用 ApplicationServices 表的 0x22 服务行和 DID-Session 支持矩阵
- Boot 域使用 BootServices 表的 0x22 服务行和 DID-Session 支持矩阵
- Boot 域的 DID 可读范围与会话支持可能与 APP 域完全不同，必须从 Boot 表重新读取
- 两个域的用例集之间用 `---` 分隔，Boot 域用例编号接续 APP 域

## 寻址规则

- **Physical 寻址**：生成完整测试集
- **Functional 寻址**：即使 Functional Request = N，仍需生成功能寻址用例集（全部预期 No_Response）
- 当 Functional Request = Y 时，功能寻址用例必须是物理寻址的完整镜像（每个 DID × 每个会话全部覆盖）
- Functional 用例 ID 编号连续接续 Physical，不从 001 重新开始

---

## 生成分类（共 7 类）

按以下固定顺序逐类生成，每个分类使用 `## N.N` 作为标题（如 `## 1.1 Session Layer Test`）。

---

### 分类 1: Session Layer Test (APP)
#### 用例数量规则

- **正向用例**: `Npos` = 可读 DID × 支持的会话数（每个可读 DID 在每个支持的会话下各 1 条）
- **负向用例（不支持会话）**: `Nneg_sess` = 每个可读 DID × 每个不支持的会话各 1 条
  - 即：即使某个会话不支持 0x22 服务，也必须对每个可读 DID 单独生成一条 NRC 用例
  - 示例：若 Programming 会话不支持，15 个 DID 各生成 1 条 → 15 条 NRC 用例
- **总数 = Npos + Nneg_sess**

#### 生成顺序

按会话分组，每组内按 DID 排序：
1. Default Session 正向（每个可读 DID 1 条）
2. Extended Session 正向（每个可读 DID 1 条）
3. Programming Session 负向（每个可读 DID 1 条 NRC）

#### 用例命名规则

- 正向：`<CurrentSessionName> Session support the 0x22 service read DID 0x<DID>`
  - 示例：`Default Session support the 0x22 service read DID 0xF186`
- 负向（会话不支持）：`<CurrentSessionName> Session nonsupport 0x22 service read DID 0x<DID>`
  - 示例：`Programming Session nonsupport 0x22 service read DID 0xF180`

#### 测试步骤模板

**A. 支持会话正向（可读 DID）**
```
1. 进入目标会话（按标准路径）
2. Send DiagBy[Physical]Data[22 <DID_H> <DID_L>];
```

**B. 不支持的会话（每个 DID 独立一条）**
```
1. 进入不支持的会话（如 Programming）
2. Send DiagBy[Physical]Data[22 <DID_H> <DID_L>];
```

#### Check 规则

**A. 支持会话正向：**
- `Check DiagData[62 <DID_H> <DID_L> <DataContent>]Within[50]ms;`
- DataContent 长度 = DID 的 Byte Length
- 固定值用实际值（如 F186=当前会话号 01/02/03），可变值用 xx

**B. 不支持的会话（每个 DID 独立一条）：**
- `Check DiagData[7F 22 31]Within[50]ms;`
- **注意**：即使服务级表中该会话标记为 N（不支持 0x22 服务），负向用例也必须返回 NRC 0x31（conditionsNotCorrect），而不是 0x7F（serviceNotSupportedInActiveSession）。原因是 0x22 的会话不支持在 DID 级别判断，属于条件不满足而非服务本身不支持。

#### 特殊规则

1. 每个 DID 单独一条用例，不可合并
2. DID 数据内容中，固定值用实际值，可变值用 xx
3. 若 DID 支持 Read 但未定义 Default 值，用 xx 占位
4. 特殊 DID 示例：DID 0xF186（Active Diagnostic Session），1 字节，值=当前会话号（01/02/03）
5. DID 列表从 DID 表（Sheet 含 "DID" 或 "0x22"/"0x2E"）读取，包括 Basic DIDs 和 RDBI DIDs
6. **Programming Session 必须对每个可读 DID 都生成负向用例**，不是只选 1 个代表性 DID
7. **APP 不支持会话的 NRC 统一为 0x31**，不可使用 0x7F

#### Unsupported DID 测试（APP 域）

除可读 DID 外，还需从 DID 表提取 **ECU 支持 = N** 的 DID 列表（即标准中定义了该 DID，但当前 ECU 不支持）。

- 在 Default Session 下，对每个 unsupported DID 生成 1 条读取用例
- 预期响应：`Check DiagData[7F 22 31]Within[50]ms;`
- 用例命名：`Default Session unsupported DID 0x<DID> returns NRC 0x31`
- 这些用例排在正向用例之后、不支持会话负向用例之前
- **总数 = unsupported DID 数量**

---

### 分类 2: Secure Access Test
#### 用例数量规则

- **即使所有 DID 的 Read Access Level 均为 Level0（无安全限制），也必须生成 Secure Access 测试用例**
- 用例目的：验证安全解锁流程后，DID 读取行为仍然正确
- **APP 域**：在 Extended Session 中执行 Seed/Key 解锁，然后读取所有可读 DID → **总数 = APP 可读 DID 数**
- **Boot 域**：在 Programming Session 中执行 Boot 级 Seed/Key 解锁，然后读取所有 Boot 可读 DID → **总数 = Boot 可读 DID 数**
- 若有 DID 的 Read Access Level 包含安全限制（如 Locked/L2 等），也按同一模板生成

#### 用例命名规则

- APP 域：`Security access Lx unlock supports 0x22 service read DID 0x<DID>`
  - 示例：`Security access L2 unlock supports 0x22 service read DID 0xF198`
- Boot 域：`Boot Security access Lx unlock supports 0x22 service read DID 0x<DID>`
  - 示例：`Boot Security access L12 unlock supports 0x22 service read DID 0xF180`

#### 测试步骤模板

**APP 域（Extended Session）**：
```
1. 进入 Extended Session（按标准路径）
2. Send DiagBy[Physical]Data[27 <SeedSub>]AndCheckResp[PostiveResponse];
3. Send Security Right KeyBy[Physical]Level[<KeySub>];
4. Send DiagBy[Physical]Data[22 <DID_H> <DID_L>];
```

**Boot 域（Programming Session）**：
```
1. 进入 Boot Programming Session（按 Boot 标准路径）
2. Send DiagBy[Physical]Data[27 <BootSeedSub>]AndCheckResp[PostiveResponse];
3. Send Security Right KeyBy[Physical]Level[<BootKeySub>];
4. Send DiagBy[Physical]Data[22 <DID_H> <DID_L>];
```

#### Check 规则

- 第 3 步：`Check DiagData[67 <KeySub>]Within[50]ms;`
- 第 4 步：`Check DiagData[62 <DID_H> <DID_L> <DataContent>]Within[50]ms;`

#### 特殊规则

1. 安全等级从 DID 表的 Read Access Level 字段读取，不写死
2. APP 域 SeedSub/KeySub：从 ApplicationServices 的安全等级表获取（如 L1 → 27 01/27 02，L2 → 27 03/27 04）
3. Boot 域 SeedSub/KeySub：从 BootServices 的安全等级表获取（如 L11 → 27 11/27 12，与 APP 域可能不同）
4. **Level0 DID 也必须生成安全访问用例**，验证安全解锁不会破坏正常读取

---

### 分类 3: Boot Session Layer Test

#### 用例数量规则

- **与分类 1 结构完全相同**，但使用 Boot 域的 DID-Session 支持矩阵
- `Npos_boot` = Boot 可读 DID × Boot 支持的会话数
- `Nneg_boot` = Boot 不可读 DID × 对应会话的 NRC 用例
- Boot 域的标准进入路径：`Default → Extended → Programming → Default(Boot)`

#### 生成顺序

按 Boot 会话分组：
1. Boot Default Session 正向（每个 Boot 可读 DID 1 条）
2. Boot Programming Session 正向（每个 Boot 可读 DID 1 条）
3. Boot Extended Session（如支持）正向
4. Boot 各会话负向（DID 在该 Boot 会话下不可读 → NRC 0x31）

#### 用例命名规则

- 正向：`Boot <SessionName> Session support the 0x22 service read DID 0x<DID>`
  - 示例：`Boot Programming Session support the 0x22 service read DID 0xF180`
- 负向：`Boot <SessionName> Session nonsupport read DID 0x<DID> (APP only DID)`
  - 示例：`Boot Programming Session nonsupport read DID 0xF189 (APP only DID)`

#### 测试步骤模板

**A. Boot 正向（可读 DID）**
```
1. Send DiagBy[Physical]Data[10 01]
2. Delay[1000]ms;
3. Send DiagBy[Physical]Data[10 03]
4. Send DiagBy[Physical]Data[10 02]
5. (如需回到 Boot Default: Send DiagBy[Physical]Data[10 01])
6. Send DiagBy[Physical]Data[22 <DID_H> <DID_L>];
```

**B. Boot 负向（不可读 DID）**
- 同上步骤，但预期 `Check DiagData[7F 22 31]Within[50]ms;`

#### Check 规则

- Boot 正向：`Check DiagData[62 <DID_H> <DID_L> <DataContent>]Within[50]ms;`
- Boot 负向：`Check DiagData[7F 22 31]Within[50]ms;`

#### 特殊规则

1. Boot 域的 DID 列表必须从 BootServices 表重新读取，不能复用 APP 域的列表
2. 某些 DID 仅在 APP 域可读（Boot 列表中标记为 N），这些 DID 在 Boot 会话下必须生成 NRC 0x31 负向用例
3. Boot 域支持的会话可能包含 Programming Session（与 APP 域不同）

#### Unsupported DID 测试（Boot 域）

与 APP 域类似，Boot 域也需测试 unsupported DID：
- 在 Boot Default Session 下，对每个 Boot 域 unsupported DID 生成 1 条读取用例
- 预期响应：`Check DiagData[7F 22 31]Within[50]ms;`
- 用例命名：`Boot Default Session unsupported DID 0x<DID> returns NRC 0x31`
- 这些用例排在 Boot 正向用例之后、APP-only DID 负向用例之前

---

### 分类 4: DID Range Test
#### 用例数量规则

- **APP 域**：每个支持 0x22 的会话各 1 条 → 通常 Default + Extended = **2 条**（Programming 如支持也加 1 条）
- **Boot 域**：每个 Boot 支持 0x22 的会话各 1 条 → 通常 Default + Programming + Extended = **3 条**

#### 用例命名规则

- APP Default 物理寻址：`DID range traversal test by physical addressing in Default Session`
- APP Extended 物理寻址：`DID range traversal test by physical addressing in Extended Session`
- Boot Default 物理寻址：`Boot DID range traversal test by physical addressing in Default Session`
- Boot Programming 物理寻址：`Boot DID range traversal test by physical addressing in Programming Session`
- Boot Extended 物理寻址：`Boot DID range traversal test by physical addressing in Extended Session`

#### 测试步骤模板

```
1. 进入支持的会话
2. Send DIDTraversalBy[Physical]Service[0x22]Excluding[<AllSupportedDIDList>]AndCheckResp[0x31];
```

其中：
- `<AllSupportedDIDList>` = 所有 Support=Y 的 DID（含 Basic DIDs 和 RDBI DIDs）
  - 示例：`F1 86 F1 87 F1 88 F1 89 F1 90 F1 91 F1 92 F1 93 ...`
- Boot 版本的 Excluding 列表使用 Boot 域的 DID 列表

#### Check 规则

- 第 1 步：检查进入会话的正响应
- 第 2 步：不单独写 Expected Output（AndCheckResp 已内含检查）
  - 遍历不支持的 DID → `7F 22 31`

#### 特殊规则

1. Excluding 列表必须包含所有 Support=Y 的 DID，包括 3.1(Basic DIDs) 和 3.2(RDBI DIDs) Sheet 中的
2. Boot 域 DID Range 使用 Boot 域的 Excluding 列表

---

### 分类 5: Incorrect Diagnostic Command Test
#### 用例数量规则

- **APP 域**：每个支持 0x22 的会话各 2 条（SF_DL > 3 + SF_DL < 3）→ 通常 Default + Extended = **4 条**
- **Boot 域**：每个 Boot 支持 0x22 的会话各 2 条 → 通常 Default + Programming + Extended = **6 条**

| 序号 | 错误类型 | 描述 |
|------|---------|------|
| 1 | SF_DL > 3 | 有效负载长度大于合法值 |
| 2 | SF_DL < 3 | 有效负载长度小于合法值 |

#### 用例命名规则

1. `<SessionName> Session invalid SF_DL > 3 triggers NRC 0x13`
2. `<SessionName> Session invalid SF_DL < 3 triggers NRC 0x13`

Boot 域加前缀 `Boot `。每个会话独立生成一对用例。

#### 测试步骤模板

选择一个代表性可读 DID（如 F1 86）进行测试。

**前置步骤：** 进入对应会话（按标准路径）

**A. SF_DL > 3**
```
Send DiagBy[Physical]Data[22 F1 86]WithLen[4];
```

**B. SF_DL < 3**
```
Send DiagBy[Physical]Data[22 F1]WithLen[2];
```

APP 域在 Default 和 Extended 会话下分别生成；Boot 域在 Default、Programming、Extended 会话下分别生成。Boot 域的进入路径使用 Boot 标准路径。

#### Check 规则

| 错误类型 | Expected Output |
|---------|----------------|
| SF_DL > 3 | `Check DiagData[7F 22 13]Within[50]ms;` |
| SF_DL < 3 | `Check DiagData[7F 22 13]Within[50]ms;` |

#### 特殊规则

1. 0x22 的合法 SF_DL 为 3 字节（SID + DID 2 字节）
2. 不存在 NRC 0x12（0x22 无子功能概念）
3. SF_DL 错误使用 `Send DiagBy...WithLen[...]`
4. Boot 域必须独立生成 2 条 Incorrect Command 用例

#### CAN DLC 测试（仅 CAN 协议项目适用）

当协议为 CAN（非 LIN）时，还需额外生成 DLC 级别测试用例：

| 序号 | 错误类型 | 描述 |
|------|---------|------|
| 3 | DLC < 8 | CAN帧DLC不足8字节，ISO-TP无法解析 |
| 4 | DLC > 8 | CAN帧DLC超过8字节（正常响应） |

- **DLC < 8**：使用原始 CAN 帧格式 `Send Msg[<CAN_ID>]Data[03 22 F1 86]WithDLC[7]`，预期 `Check No_Response Within[1000]ms;`
- **DLC > 8**：使用原始 CAN 帧格式 `Send Msg[<CAN_ID>]Data[03 22 F1 86 00 00 00 00 00]WithDLC[9]`，预期正常正响应
- CAN_ID 从参数表 General 中获取（物理寻址ID）
- LIN 协议项目不生成 DLC 测试用例

---

### 分类 6: NRC Priority Test
#### 用例数量规则

- **APP 域**：每个支持 0x22 的会话各 1 条 → 通常 Default + Extended = **2 条**
- **Boot 域**：每个 Boot 支持 0x22 的会话各 1 条 → 通常 Default + Programming + Extended = **3 条**

#### 用例命名规则

- APP：`<SessionName> Session NRC priority test for service 0x22`
- Boot：`Boot <SessionName> Session NRC priority test for service 0x22`

#### 测试步骤

在对应会话下，发送长度错误的 0x22 请求（如 SF_DL < 3），验证 ECU 优先返回 NRC 0x13 而非其他 NRC。

```
1. 进入目标会话（按标准路径）
2. Send DiagBy[Physical]Data[22 F1]WithLen[2];
```

#### Check 规则

```
1. Check DiagData[<Session Positive Response>]Within[50]ms;
2. Check DiagData[7F 22 13]Within[50]ms;
```

#### 特殊规则

1. NRC 0x13（消息长度错误）的优先级高于 NRC 0x31（DID 不支持）等
2. 此用例验证 ECU 正确的 NRC 优先级处理
3. APP 和 Boot 域分别在各支持会话下生成

---

## 会话进入标准路径

为统一生成，进入各会话的标准路径如下：

| 目标会话 | 标准进入步骤 |
|---------|------------|
| Default（0x01） | `Send DiagBy[Physical]Data[10 01];` |
| Extended（0x03） | `Send DiagBy[Physical]Data[10 03];`（直接进入，无需先经 Default） |
| Programming（0x02） | `Send DiagBy[Physical]Data[10 01];` → `Send DiagBy[Physical]Data[10 03];` → `Send DiagBy[Physical]Data[10 02];` |

**注意**：
- 会话切换之间**不使用 Delay**，除非参数表或特定测试场景明确要求
- 如果从 Default 进入 Extended，直接 `10 03` 即可，无需先 `10 01` 再 `10 03`
- Boot 域进入路径：先进入 Programming Session 触发 Boot 模式，再切换到目标 Boot 会话

---

## 功能寻址用例生成规则

当 `Functional Request = 支持` 时：
1. 将所有 Physical 用例复制一份（完整镜像，不可简化为代表性子集）
2. 发送函数中 `[Physical]` 改为 `[Function]`
3. Case ID 中 `Phy` 改为 `Fun`，编号连续（不从001重启，接续 Physical 最后编号）
4. DID 遍历功能寻址版同样使用 `DIDTraversalBy[Function]`
5. **安全访问混合寻址**：功能寻址用例中，Session 进入和 DID 读取使用 `[Function]`，但 SecurityAccess（Seed/Key）步骤仍使用 `[Physical]`，因为安全访问通常要求物理寻址

当 `Functional Request = 不支持` 时：
- **仍需生成功能寻址用例集**，分 APP 域和 Boot 域两部分：
- **APP 域功能寻址**（分以下 3 个子类）：
  1. **代表性 DID 读取**（Default 会话，选取 2-3 个代表性 DID）：预期全部 No_Response
  2. **DID Range 遍历**（1 条）：`DIDTraversalBy[Function]` → 全部 No_Response
  3. **Incorrect Command**（1-2 条）：SF_DL 错误 → 全部 No_Response
- **Boot 域功能寻址**（必须生成完整覆盖）：
  1. **所有 Boot DID 读取**：每个 Boot 可读 DID × 每个 Boot 支持会话（Default/Programming/Extended）各 1 条，预期全部 No_Response
  2. **DID Range 遍历**（1 条）：`DIDTraversalBy[Function]` → 全部 No_Response
  3. **Incorrect Command**（2 条）：SF_DL > 3 和 SF_DL < 3 → 全部 No_Response
- 所有 Functional 用例预期输出均为 `Check No_Response Within[1000]ms;`
- APP 域不需要对每个 DID × 每个会话生成完整矩阵，Boot 域需要

---

## DID 数据填充规则

**核心要求：预期输出中的数据必须尽可能精确，尽量减少 xx 占位符的使用。**

优先级从高到低：

| 优先级 | 场景 | 填充方式 | 说明 |
|--------|------|---------|------|
| 1 | DID 数据为固定值 | 使用实际值 | 如 F186=当前会话号(01/03)，F160=01 |
| 2 | DID 有定义 DefaultValue | 使用 DefaultValue | 从 DID 表的 DefaultValue 列读取，如 F197="HOD"，F18A="8DR" |
| 3 | DID 有 Default value(Phy.) | 使用物理默认值 | 从参数表转换为 HEX 填充 |
| 4 | DID 数据为可变值且无默认值 | 使用 xx 占位 | 最后手段，仅当确实无法获取精确值时使用 |

**重要规则**：
- ASCII 类型 DID：如果有默认值，将 ASCII 字符串逐字节转换为 HEX（如 "HOD" → `48 4F 44`）
- 数值类型 DID：如果有默认值，按 Data Type 和 Formula 转换为 HEX
- BCD 类型 DID：使用 BCD 编码填充
- 如果参数表中有多个子行（同一 DID 多个字节定义），每个字节按子行定义分别填充
- **数据长度必须精确匹配 DID 的 Byte Length**，xx 的数量 = Byte Length - 已知字节数

---

## 生成注意事项

1. **顶级标题使用 `#`**：如 `# 1. Application Service_Physical Addressing`、`# 2. Application Service_Functional Addressing`、`# 3. Boot Service_Physical Addressing`、`# 4. Boot Service_Functional Addressing`
2. **分类标题使用 `##`**：如 `## 1.1 Session Layer Test`、`## 1.2 Secure Access Test` 等
3. **各大组之间用 `---` 分隔**
4. **无符合条件的用例时使用 `>` 引用**：如 `> 无符合条件的用例。`
5. **Case ID 不可重复**，物理寻址 `Diag_0x22_Phy_001` 起递增，功能寻址 `Diag_0x22_Fun_001` 起递增
2. **编号从 001 开始**，优先编写所有 Physical 用例，再编写 Functional 用例，Functional 编号连续接续 Physical（不从 001 重启）
3. **每个 Send 都要有对应 Check**，除以下豁免：
   - `Delay[...]ms` 不写 Check
   - 带 `AndCheckResp[...]` 的发送函数不单独写 Check
4. **DID 列表从 DID 表读取**，包括 Basic DIDs 和 RDBI DIDs 两个 Sheet
5. **0x22 无子功能概念**，不存在 NRC 0x12，不支持的 DID 返回 NRC 0x31
6. **输出格式严格为 pipe table**，列顺序：`| Case ID | Case名称 | 测试步骤 | 预期输出 |`
7. **步骤中换行使用 `<br>` 标记**，不用 `\n`
8. **不要生成任何"参数提取结果"或"分析"段落**，直接输出测试用例表格

---

## 分类汇总

| 分类 | 描述 | 用例数量公式 |
|------|------|-------------|
| 1. Session Layer (APP) | 可读 DID × 支持会话 + 每个可读 DID × 不支持会话 + unsupported DID | `|DIDs| × |支持会话| + |DIDs| × |不支持会话| + |unsupported DIDs|` |
| 2. Security Access (APP+Boot) | APP 可读 DID + Boot 可读 DID（含 Level0） | `|APP DIDs| + |Boot DIDs|` |
| 3. Boot Session Layer | Boot 可读 DID × Boot 支持会话 + 不可读 NRC + unsupported DID | `|Boot DIDs| × |Boot支持会话| + |Boot不可读DIDs| + |Boot unsupported DIDs|` |
| 4. DID Range | APP 每支持会话 1 条 + Boot 每支持会话 1 条 | `|APP支持会话| + |Boot支持会话|` |
| 5. Incorrect Command | APP 每支持会话 2 条 + Boot 每支持会话 2 条 | `|APP支持会话| × 2 + |Boot支持会话| × 2` |
| 6. NRC Priority | APP 每支持会话 1 条 + Boot 每支持会话 1 条 | `|APP支持会话| + |Boot支持会话|` |
| 7. Functional Addressing | APP 代表性 DID + DID Range + Incorrect Command + Boot 完整覆盖 | ~5-9 条 (APP) + `\|Boot DIDs\| × \|Boot支持会话\| + 3` (Boot) |
