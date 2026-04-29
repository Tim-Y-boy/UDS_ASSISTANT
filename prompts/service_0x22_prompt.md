# Service 0x22 ReadDataByIdentifier — 用例生成规则

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
- 两个域的用例集之间用注释行分隔，Boot 域用例编号接续 APP 域

## 寻址规则

- **Physical 寻址**：生成完整测试集
- **Functional 寻址**：即使 Functional Request = N，仍需生成完整的功能寻址用例集（全部预期 No_Response）
- Functional 用例集不重复每个 DID × 每个会话的组合，仅选取代表性 DID 在 Default 会话下测试
- Functional 用例集包括：代表性 DID 读取 + DID Range + Incorrect Command

---

## 生成分类（共 7 类）

按以下固定顺序逐类生成，每个分类之间用 `--service ID 0x22 <分类名>` 分隔。

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

**B. 不支持的会话：**
- `Check DiagData[7F 22 7F]Within[50]ms;`

#### 特殊规则

1. 每个 DID 单独一条用例，不可合并
2. DID 数据内容中，固定值用实际值，可变值用 xx
3. 若 DID 支持 Read 但未定义 Default 值，用 xx 占位
4. 特殊 DID 示例：DID 0xF186（Active Diagnostic Session），1 字节，值=当前会话号（01/02/03）
5. DID 列表从 DID 表（Sheet 含 "DID" 或 "0x22"/"0x2E"）读取，包括 Basic DIDs 和 RDBI DIDs
6. **Programming Session 必须对每个可读 DID 都生成负向用例**，不是只选 1 个代表性 DID

---

### 分类 2: Secure Access Test
#### 用例数量规则

- 仅对 Read Access Level 包含安全限制（如 Locked/L2 等）的 DID 生成
- **总数 = N_did_need_security**

#### 用例命名规则

`Security access Lx unlock supports 0x22 service read DID 0x<DID>`
- 示例：`Security access L2 unlock supports 0x22 service read DID 0xF198`

#### 测试步骤模板

```
1. 进入支持的会话（通常 Extended）
2. Send DiagBy[Physical]Data[27 <SeedSub>]AndCheckResp[PostiveResponse];
3. Send Security Right KeyBy[Physical]Level[<KeySub>];
4. Send DiagBy[Physical]Data[22 <DID_H> <DID_L>];
```

#### Check 规则

- 第 3 步：`Check DiagData[67 <KeySub>]Within[50]ms;`
- 第 4 步：`Check DiagData[62 <DID_H> <DID_L> <DataContent>]Within[50]ms;`

#### 特殊规则

1. 安全等级从 DID 表的 Read Access Level 字段读取，不写死
2. SeedSub/KeySub 对应关系：L1 → 27 01/27 02，L2 → 27 03/27 04 等

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

---

### 分类 4: DID Range Test
#### 用例数量规则

**APP 域固定 1 条（物理寻址），Boot 域固定 1 条（物理寻址）**

#### 用例命名规则

- APP 物理寻址：`DID range traversal test by physical addressing`
- Boot 物理寻址：`Boot DID range traversal test by physical addressing`

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

**APP 域固定 2 条 + Boot 域固定 2 条**

| 序号 | 错误类型 | 描述 |
|------|---------|------|
| 1 | SF_DL > 3 | 有效负载长度大于合法值 |
| 2 | SF_DL < 3 | 有效负载长度小于合法值 |

#### 用例命名规则

1. `Valid SF_DL=3, invalid SF_DL > 3 triggers NRC 0x13`
2. `Valid SF_DL=3, invalid SF_DL < 3 triggers NRC 0x13`

Boot 域加前缀 `Boot `。

#### 测试步骤模板

选择一个代表性可读 DID（如 F1 86）进行测试。

**前置步骤：** 进入支持 0x22 的当前会话

**A. SF_DL > 3**
```
Send DiagBy[Physical]Data[22 F1 86]WithLen[4];
```

**B. SF_DL < 3**
```
Send DiagBy[Physical]Data[22 F1]WithLen[2];
```

Boot 域的进入路径使用 Boot 标准路径。

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

---

### 分类 6: NRC Priority Test
#### 用例数量规则

**固定 1 条**（APP 域）

#### 用例命名规则

`NRC priority test for service 0x22`

#### 测试步骤

在 Default 会话下，发送长度错误的 0x22 请求（如 SF_DL < 3），验证 ECU 优先返回 NRC 0x13 而非其他 NRC。

```
1. Send DiagBy[Physical]Data[10 01]
2. Send DiagBy[Physical]Data[22 F1]WithLen[2];
```

#### Check 规则

```
1. Check DiagData[50 01 00 32 01 F4]Within[50]ms;
2. Check DiagData[7F 22 13]Within[50]ms;
```

#### 特殊规则

1. NRC 0x13（消息长度错误）的优先级高于 NRC 0x31（DID 不支持）等
2. 此用例验证 ECU 正确的 NRC 优先级处理

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
1. 将所有 Physical 用例复制一份,物理寻址不需要回复NRC包含[0x11 (服务不支持),0x12 (子功能不支持),0x7F (当前会话服务不支持),0x7E (当前会话子功能不支持),0x31 (请求超出范围)]，此时不需要响应 <Check No_Response within [P2 server]ms;>
2. 发送函数中 `[Physical]` 改为 `[Function]`
3. Case ID 中 `Phy` 改为 `Fun`，编号重新从 001 开始
4. DID 遍历功能寻址版同样使用 `DIDTraversalBy[Function]`

当 `Functional Request = 不支持` 时：
- **仍需生成功能寻址用例集**，分以下 3 个子类：
  1. **代表性 DID 读取**（Default 会话，选取 2-3 个代表性 DID）：预期全部 No_Response
  2. **DID Range 遍历**（1 条）：`DIDTraversalBy[Function]` → 全部 No_Response
  3. **Incorrect Command**（1-2 条）：SF_DL 错误 → 全部 No_Response
- 所有 Functional 用例预期输出均为 `Check No_Response Within[1000]ms;`
- 不需要对每个 DID × 每个会话生成完整矩阵

---

## DID 数据填充规则

| 场景 | 填充方式 |
|------|---------|
| DID 有定义 Default 值 | 使用 Default 值 |
| DID 数据为固定值 | 使用实际值（如 F186=当前会话号） |
| DID 数据为可变值 | 使用 xx 占位 |
| DID 未定义 Default 值 | 使用 xx 占位 |

---

## 生成注意事项

1. **Case ID 不可重复**，物理寻址 `Diag_0x22_Phy_001` 起递增，功能寻址 `Diag_0x22_Fun_001` 起递增
2. **编号从 001 开始**，优先编写所有 Physical 用例，再编写 Functional 用例
3. **每个 Send 都要有对应 Check**，除以下豁免：
   - `Delay[...]ms` 不写 Check
   - 带 `AndCheckResp[...]` 的发送函数不单独写 Check
4. **DID 列表从 DID 表读取**，包括 Basic DIDs 和 RDBI DIDs 两个 Sheet
5. **0x22 无子功能概念**，不存在 NRC 0x12，不支持的 DID 返回 NRC 0x31
6. **输出格式严格按照 Case ID / Case名称 / 测试步骤 / 预期输出 的固定模板**

---

## 分类汇总

| 分类 | 描述 | 用例数量公式 |
|------|------|-------------|
| 1. Session Layer (APP) | 可读 DID × 支持会话 + 每个可读 DID × 不支持会话 | `|DIDs| × |支持会话| + |DIDs| × |不支持会话|` |
| 2. Security Access (APP) | 需安全解锁的 DID | `|需安全解锁的 DID|` |
| 3. Boot Session Layer | Boot 可读 DID × Boot 支持会话 + 不可读 NRC | `|Boot DIDs| × |Boot支持会话| + |Boot不可读DIDs|` |
| 4. DID Range | APP 物理 1 + Boot 物理 1 | 固定 2 条 |
| 5. Incorrect Command | APP 2 (SF_DL) + Boot 2 (SF_DL) | 固定 4 条 |
| 6. NRC Priority | NRC 优先级测试 | 固定 1 条 |
| 7. Functional Addressing | 代表性 DID + DID Range + Incorrect Command | ~5-9 条 |
