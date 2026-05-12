# Service 0x85 ControlDTCSetting — 用例生成规则

## 服务概述

- **Service ID**: 0x85
- **Service Name**: ControlDTCSetting
- **正响应 SID**: 0xC5（0x85 + 0x40）
- **负响应格式**: `7F 85 <NRC>`
- **子功能**: 01(On/启用 DTC 记录), 02(Off/禁用 DTC 记录)
- **请求格式**: `85 <Sub> FF FF FF`（DTCRecordMask，通常全 FF）
- **简化格式**: `85 <Sub>`（部分 ECU 支持，省略 DTCRecordMask 仍返回正响应）
- **合法 SF_DL**: 5 字节（SID + Sub + 3 字节 DTCRecordMask），简化版 2 字节也可接受
- **关键特性**: 禁用/启用 DTC 记录
- **通常仅 Extended 会话支持**

### 正响应格式

- `C5 <Sub>`（仅确认，无额外 payload）

### 典型 NRC

| NRC  | 含义 | 触发条件 |
|------|------|---------|
| 0x12 | Subfunction Not Supported | 发送了不支持的子功能（非 01/02） |
| 0x13 | Incorrect Message Length Or Invalid Format | 报文长度错误 |
| 0x22 | Conditions Not Correct | 前置条件不满足 |
| 0x31 | Request Out Of Range | DTCRecordMask 不支持 |
| 0x7E | Subfunction Not Supported In Active Session | 该子功能在当前会话下不支持 |
| 0x7F | Service Not Supported In Active Session | 当前会话下不支持 0x85 服务 |

---

## 软件域规则

- **必须为 APP 和 Boot 两个软件域各独立生成完整用例集**
- APP 域：0x85 通常在 Extended 会话支持
- Boot 域：0x85 通常不支持，所有测试预期 `7F 85 7F`（Physical）或 `No_Response`（Functional）
- 两个域的用例集之间用 `---` 分隔，Boot 域用例编号接续 APP 域

## 寻址规则

- **Physical 寻址**：生成完整测试集
- **Functional 寻址**：无论是否支持 Functional Request，均生成完整的功能寻址用例集
- Functional 寻址用例集中，所有测试步骤使用 `[Function]` 发送，所有预期输出为 `Check No_Response Within[1000]ms;`
- 功能寻址用例集是物理寻址用例集的完整镜像

---

## 生成分类（共 9 类）

按以下固定顺序逐类生成，每个分类使用 `## N.N` 作为标题（如 `## 1.1 Session Layer Test`）。

---

### 分类 1: Session Layer Test (APP)

#### 用例数量规则

- **正向（Extended On/Off）**: 2 条
- **负向（Default On/Off）**: 2 条
- **格式测试（省略 FF FF FF）**: 2 条
- **总数 = 6 条**

#### 用例命名规则

- 正向：`<CurrentSessionName> Session support the 0x85 service 0x<Sub> subfunction 1Case-$85`
- 负向（会话不支持）：`<CurrentSessionName> Session nonsupport 0x85 service 0x<Sub> subfunction NegativeCase-$85`
- 格式测试：`<CurrentSessionName> Session 0x85 Service format error 1Case-$85`（省略 mask 后仍返回正响应）

#### 测试步骤模板

**A. 不支持的会话（Default）**
```
1. Send DiagBy[Physical]Data[10 01];
2. Send DiagBy[Physical]Data[85 01 FF FF FF];（On）
```
```
1. Send DiagBy[Physical]Data[10 01];
2. Send DiagBy[Physical]Data[85 02 FF FF FF];（Off）
```

**B. 支持会话正向（Extended）**
```
1. Send DiagBy[Physical]Data[10 03];
2. Send DiagBy[Physical]Data[85 01 FF FF FF];（On）
```
```
1. Send DiagBy[Physical]Data[10 03];
2. Send DiagBy[Physical]Data[85 02 FF FF FF];（Off）
```

**C. 格式测试（省略 FF FF FF）**
```
1. Send DiagBy[Physical]Data[10 03];
2. Send DiagBy[Physical]Data[85 01];（省略 mask）
```
```
1. Send DiagBy[Physical]Data[10 03];
2. Send DiagBy[Physical]Data[85 02];（省略 mask）
```

#### Check 规则

**A. 不支持的会话：**
- `Check DiagData[7F 85 7F]Within[50]ms;`

**B. 支持会话正向：**
- On：`Check DiagData[C5 01]Within[50]ms;`
- Off：`Check DiagData[C5 02]Within[50]ms;`

**C. 格式测试：**
- On（省略 mask）：`Check DiagData[C5 01]Within[50]ms;`（仍返回正响应）
- Off（省略 mask）：`Check DiagData[C5 02]Within[50]ms;`（仍返回正响应）

---

### 分类 2: SPRMIB Test (APP)

#### 用例数量规则

- Default Session 负向（81/82）：2 条
- Extended Session 正向（81/82）：2 条
- **总数 = 4 条**

#### 用例命名规则

- 负向（会话不支持）：`<SessionName> Session nonsupport 0x85 service 0x<Sub> subfunction with SPRMIB NegativeCase-$85`
- 正向：`<SessionName> Session support 0x85 service 0x<Sub> with SPRMIB 1Case-$85`

#### 测试步骤模板

**A. Default Session SPRMIB（负向）**
```
1. Send DiagBy[Physical]Data[10 01];
2. Send DiagBy[Physical]Data[85 81 FF FF FF];
```
```
1. Send DiagBy[Physical]Data[10 01];
2. Send DiagBy[Physical]Data[85 82 FF FF FF];
```

**B. Extended Session SPRMIB（正向）**
```
1. Send DiagBy[Physical]Data[10 03];
2. Send DiagBy[Physical]Data[85 81 FF FF FF];
```
```
1. Send DiagBy[Physical]Data[10 03];
2. Send DiagBy[Physical]Data[85 82 FF FF FF];
```

#### Check 规则

**A. Default（不支持）：**
- `Check DiagData[7F 85 7F]Within[50]ms;`

**B. Extended（支持）：**
- `Check No_Response Within[1000]ms;`

---

### 分类 3: Secure Access Test (APP)

#### 用例数量规则

- L1 解锁 × 01/02/81/82 各 1 条
- **总数 = 4 条**

#### 用例命名规则

`Security access to L1 unlock supports 0x85 service 0x<Sub> subfunction 1Case-$85`

#### 测试步骤模板

```
1. Send DiagBy[Physical]Data[10 03];
2. Send DiagBy[Physical]Data[27 01]AndCheckResp[1];
3. Send Security Right KeyBy[Physical]Level[0x2];
4. Send DiagBy[Physical]Data[85 <Sub> FF FF FF];（或 85 81/82 FF FF FF）
```

#### Check 规则

- 第 3 步：`Check DiagData[67 02]Within[50]ms;`
- 第 4 步（01/02）：`Check DiagData[C5 <Sub>]Within[50]ms;`
- 第 4 步（81/82 SPRMIB）：`Check No_Response Within[1000]ms;`

---

### 分类 4: Sub-function Traversal Test (APP)

#### 用例数量规则

**固定 1 条**

#### 用例命名规则

`Subfunction traversal test in the Extended Session NegativeCase-$85`

#### 测试步骤模板

```
1. Send DiagBy[Physical]Data[10 03];
2. Send 0x85SubTraversalBy[Physical]Excluding[01 02 81 82]AndCheckResp[0x12];
```

#### Check 规则

- 不支持的子功能 → `7F 85 12`

---

### 分类 5: Incorrect Diagnostic Command Test (APP)

#### 用例数量规则

**固定 2 条**

| 序号 | 错误类型 | 描述 |
|------|---------|------|
| 1 | SF_DL > 5 | 有效负载长度大于合法值 |
| 2 | SF_DL < 5 | 有效负载长度小于合法值（注意：省略 mask 的 85 01 不是 SF_DL 错误） |

#### 用例命名规则

1. `Valid SF_DL=5, invalid SF_DL > 5, and those with invalid equivalence class SF_DL=6 NegativeCase-$85`
2. `Valid SF_DL=5, invalid SF_DL < 5, and those with invalid equivalence class SF_DL=4 NegativeCase-$85`

#### 测试步骤模板

**前置步骤：** 进入 Extended 会话

**A. SF_DL > 5**
```
Send DiagBy[Physical]Data[85 01 FF FF FF]WithLen[6];
```

**B. SF_DL < 5（但 SF_DL ≠ 2）**
```
Send DiagBy[Physical]Data[85 01 FF FF]WithLen[4];
```

#### Check 规则

| 错误类型 | Expected Output |
|---------|----------------|
| SF_DL > 5 | `Check DiagData[7F 85 13]Within[50]ms;` |
| SF_DL < 5 | `Check DiagData[7F 85 13]Within[50]ms;` |

#### 特殊规则

1. **注意**：`85 01`（SF_DL=2）在 Extended 会话下返回正响应，不是 SF_DL 错误
2. SF_DL < 5 的测试使用 SF_DL=4（`85 01 FF FF`），不是 SF_DL=2
3. SF_DL 错误使用 `Send DiagBy...WithLen[...]`

---

### 分类 6: NRC Priority Test (APP)

#### 用例数量规则

**固定 2 条**

| 序号 | 场景 | 描述 |
|------|------|------|
| 1 | NRC 13 > 12 | 发送 SF_DL=1 的 85 01，验证返回 0x13 |
| 2 | NRC 13 > 12 | 发送 SF_DL=3 的 85 02，验证返回 0x13 |

#### 用例命名规则

1. `NRC 13>12>22 NegativeCase-$85`
2. `NRC 13>12>22 NegativeCase-$85`

#### 测试步骤

**用例 1：**
```
1. Send DiagBy[Physical]Data[10 03];
2. Send DiagBy[Physical]Data[85 01]WithLen[1];
```

**用例 2：**
```
1. Send DiagBy[Physical]Data[10 03];
2. Send DiagBy[Physical]Data[85 02]WithLen[3];
```

#### Check 规则

**用例 1：**
- `Check DiagData[7F 85 13]Within[50]ms;`

**用例 2：**
- `Check DiagData[7F 85 13]Within[50]ms;`

---

### 分类 7: Functional Addressing Test (APP)

Functional 用例集是 Physical APP 用例集的完整镜像：
- 将所有 Physical APP 用例（分类 1-6）复制一份
- 所有发送函数中 `[Physical]` 改为 `[Function]`
- 所有预期输出改为 `Check No_Response Within[1000]ms;`
- 安全访问步骤仍使用 `[Physical]`
- Case ID 中 `Phy` 改为 `Fun`，编号重新从 001 开始

注意：Functional 镜像不包含 NRC Priority 用例。

---

### 分类 8: Boot Domain Test

Boot 域生成与 APP 域完全相同结构的测试集，但有以下关键差异：

#### Boot 域差异

| 项目 | APP 域 | Boot 域 |
|------|--------|---------|
| 服务支持 | Extended 支持 | **全部不支持**，所有测试预期 `7F 85 7F` 或 `No_Response` |
| 会话进入路径 | `10 03` 直接进入 Extended | `10 03 → 31 01 02 03 → 10 02` 进入 Programming |
| 安全等级 | L1（27 01 / 27 02） | LevelFBL（27 11 / 27 12） |
| Extended 格式测试 | `85 01/02` 返回 `C5 01/02` | `85 01/02` 返回 `7F 85 7F` |

#### Boot 域子分类

1. **Boot Physical - Session Layer**: Default/Programming/Extended × On/Off/FormatError = 6 条（全部 `7F 85 7F`）
2. **Boot Physical - SPRMIB**: Default/Programming/Extended × 81/82 = 6 条（全部 `7F 85 7F`）
3. **Boot Physical - Secure Access**: FBL unlock × 01/02/81/82 = 4 条（全部 `7F 85 7F`）
4. **Boot Physical - Sub-function Traversal**: 1 条（同 APP）
5. **Boot Physical - Incorrect Command**: 2 条（SF_DL 错误，同 APP）
6. **Boot Physical - NRC Priority**: 2 条（同 APP）
7. **Boot Functional**: Physical 的完整镜像，所有输出为 `Check No_Response Within[1000]ms;`

#### Boot Physical Session Layer 测试步骤模板

**Default Session（不支持）：**
```
1. Send DiagBy[Physical]Data[10 01];
2. Send DiagBy[Physical]Data[85 01 FF FF FF];
```
Check: `Check DiagData[7F 85 7F]Within[50]ms;`

**Programming Session（不支持）：**
```
1. Send DiagBy[Physical]Data[10 03];
2. Send DiagBy[Physical]Data[31 01 02 03];
3. Send DiagBy[Physical]Data[10 02];
4. Send DiagBy[Physical]Data[85 01 FF FF FF];
```
Check: `Check DiagData[7F 85 7F]Within[50]ms;`

**Extended Session 格式测试（不支持）：**
```
1. Send DiagBy[Physical]Data[10 03];
2. Send DiagBy[Physical]Data[85 01];（省略 mask）
```
Check: `Check DiagData[7F 85 7F]Within[50]ms;`

#### Boot Physical Secure Access 测试步骤模板

```
1. Send DiagBy[Physical]Data[10 03];
2. Send DiagBy[Physical]Data[31 01 02 03];
3. Send DiagBy[Physical]Data[10 02];
4. Send DiagBy[Physical]Data[27 11]AndCheckResp[1];
5. Send Security Right KeyBy[Physical]Level[0x12];
6. Send DiagBy[Physical]Data[85 01 FF FF FF];（或 02/81/82）
```
Check: `Check DiagData[7F 85 7F]Within[50]ms;`（即使 FBL 解锁，0x85 仍不支持）

---

## 会话进入标准路径

| 目标会话 | APP 域标准进入步骤 | Boot 域标准进入步骤 |
|---------|-------------------|-------------------|
| Default（0x01） | `Send DiagBy[Physical]Data[10 01];` | `Send DiagBy[Physical]Data[10 01];` |
| Extended（0x03） | `Send DiagBy[Physical]Data[10 03];` | `Send DiagBy[Physical]Data[10 03];` |
| Programming（0x02） | `10 03 → 31 01 02 03 → 10 02` | `10 03 → 31 01 02 03 → 10 02` |

---

## 生成注意事项

1. **Case ID 不可重复**，物理寻址 `Diag_0x85_Phy_001` 起递增，功能寻址 `Diag_0x85_Fun_001` 起递增
2. **编号从 001 开始**，顺序为：APP Physical → APP Functional → Boot Physical → Boot Functional
3. **格式测试（85 01/02 省略 mask）是 Session Layer 的一部分**，不是 Incorrect Command
4. **85 01（SF_DL=2）不是 SF_DL 错误**，ECU 可能接受省略 DTCRecordMask 的请求
5. **Boot 域所有 0x85 测试均返回 7F 85 7F**（不支持）
6. **Boot 域安全等级为 LevelFBL（27 11/27 12）**
7. **DTC Setting Function Test（完整功能验证）作为可选扩展**，如果参数表提供了 DTC 和故障触发信息
8. **输出格式严格为 pipe table**，列顺序：`| Case ID | Case名称 | 测试步骤 | 预期输出 |`
9. **顶级标题使用 `#`**：如 `# 1. Application Service_Physical Addressing`、`# 2. Application Service_Functional Addressing` 等
10. **分类标题使用 `##`**：如 `## 1.1 Session Layer Test` 等
11. **各大组之间用 `---` 分隔**
12. **无符合条件的用例时使用 `>` 引用**
13. **步骤中换行使用 `<br>` 标记**，不用 `\n`

---

## 分类汇总

| 分类 | 描述 | APP Physical | APP Functional | Boot Physical | Boot Functional |
|------|------|-------------|---------------|--------------|----------------|
| 1. Session Layer | On/Off + 格式测试 | 6 | 6 | 6 | 6 |
| 2. SPRMIB | 81/82 测试 | 4 | 4 | 6 | 6 |
| 3. Secure Access | L1/FBL 解锁 | 4 | 2 | 4 | 2 |
| 4. Sub Traversal | 子功能遍历 | 1 | 1 | 1 | 1 |
| 5. Incorrect Command | SF_DL 错误 | 2 | 2 | 2 | 2 |
| 6. NRC Priority | NRC 优先级 | 2 | - | 2 | - |
| **小计** | | **19** | **15** | **21** | **17** |
| **总计** | **~72 条** | | | | |

注意：Boot Physical 21 条包含 SPRMIB 6 条（Default/Programming/Extended × 81/82），比 APP 的 4 条多 2 条因为 Boot 需要测试 Programming 会话。
