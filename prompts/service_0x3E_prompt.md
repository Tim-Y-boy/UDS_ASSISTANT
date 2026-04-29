# Service 0x3E TesterPresent — 用例生成规则

## 服务概述

- **Service ID**: 0x3E
- **Service Name**: TesterPresent
- **正响应 SID**: 0x7E（0x3E + 0x40）
- **负响应格式**: `7F 3E <NRC>`
- **子功能**: 0x00(ZeroSubFunction)
- **SPRMIB**: 支持 0x80（0x3E 80 → 无响应）
- **请求格式**: `3E 00` 或 `3E 80`
- **合法 SF_DL**: 2 字节
- **关键特性**: 用于维持非默认会话（防止 S3 超时）；支持物理和功能寻址
- **通常在 Default、Extended 和 Programming 会话下都支持**

### 正响应格式

- `7E 00`（仅确认，无额外 payload）
- SPRMIB 模式（3E 80）：无响应

### 典型 NRC

| NRC  | 含义 | 触发条件 |
|------|------|---------|
| 0x12 | Subfunction Not Supported | 发送了 0x3E 不支持的子功能（非 0x00/0x80） |
| 0x13 | Incorrect Message Length Or Invalid Format | 报文长度错误（SF_DL ≠ 2） |

---

## 软件域规则

- **必须为 APP 和 Boot 两个软件域各独立生成完整用例集**
- APP 域使用 ApplicationServices 表的 0x3E 服务行
- Boot 域使用 BootServices 表的 0x3E 服务行
- 两个域的用例集之间用注释行分隔，Boot 域用例编号接续 APP 域

## 寻址规则

- **Physical 寻址**：生成完整测试集
- **Functional 寻址**：无论是否支持 Functional Request，均生成完整的功能寻址用例集
- Functional 寻址用例集中，所有测试步骤使用 `[Function]` 发送，所有预期输出为 `Check No_Response Within[1000]ms;`
- 功能寻址用例集是物理寻址用例集的完整镜像

---

## 生成分类（共 9 类）

按以下固定顺序逐类生成，每个分类之间用 `--service ID 0x3E <分类名>` 分隔。

---

### 分类 1: Session Layer Test (APP)

#### 用例数量规则

- 对每个支持的会话（Default、Extended、Programming）各 1 条
- **总数 = Nsupported_sessions**（通常 3 条）

#### 用例命名规则

- `<CurrentSessionName> Session support the 0x3E service 1Case-$3E`
  - 示例：`Default Session support the 0x3E service 1Case-$3E`
  - 示例：`Extended Session support the 0x3E service 1Case-$3E`
  - 示例：`Programming Session support the 0x3E service 1Case-$3E`

#### 测试步骤模板

**Default Session：**
```
1. Send DiagBy[Physical]Data[10 01];
2. Send DiagBy[Physical]Data[3E 00];
```

**Extended Session：**
```
1. Send DiagBy[Physical]Data[10 03];
2. Send DiagBy[Physical]Data[3E 00];
```

**Programming Session：**
```
1. Send DiagBy[Physical]Data[10 03];
2. Send DiagBy[Physical]Data[31 01 02 03];
3. Send DiagBy[Physical]Data[10 02];
4. Send DiagBy[Physical]Data[3E 00];
```

#### Check 规则

- 第 2/4 步：`Check DiagData[7E 00]Within[50]ms;`

---

### 分类 2: SPRMIB Test (APP)

#### 用例数量规则

- 对每个支持的会话各 1 条
- **总数 = Nsupported_sessions**（通常 3 条）

#### 用例命名规则

- `<CurrentSessionName> Session support the 0x3E service with SPRMIB 1Case-$3E`

#### 测试步骤模板

**Default Session：**
```
1. Send DiagBy[Physical]Data[10 01];
2. Send DiagBy[Physical]Data[3E 80];
```

**Extended Session：**
```
1. Send DiagBy[Physical]Data[10 03];
2. Send DiagBy[Physical]Data[3E 80];
```

**Programming Session：**
```
1. Send DiagBy[Physical]Data[10 03];
2. Send DiagBy[Physical]Data[31 01 02 03];
3. Send DiagBy[Physical]Data[10 02];
4. Send DiagBy[Physical]Data[3E 80];
```

#### Check 规则

- `Check No_Response Within[1000]ms;`

---

### 分类 3: Secure Access Test (APP)

#### 用例数量规则

**固定 2 条**（3E 00 和 3E 80 各 1 条）

#### 用例命名规则

`0x3E service keeps the 0x27 service unlocked state 1Case-$3E`

#### 测试步骤模板

**A. 3E 00 维持安全状态：**
```
1. Send DiagBy[Physical]Data[10 03];
2. Send DiagBy[Physical]Data[27 01]AndCheckResp[1];
3. Send Security Right KeyBy[Physical]Level[0x2];
4. Delay[1000]ms;
5. Send DiagBy[Physical]Data[3E 00];
6. Delay[<S3 - delta>]ms;（如 4900ms）
7. Send DiagBy[Physical]Data[22 F1 86];
```

**B. 3E 80 维持安全状态：**
```
1. Send DiagBy[Physical]Data[10 03];
2. Send DiagBy[Physical]Data[27 01]AndCheckResp[1];
3. Send Security Right KeyBy[Physical]Level[0x2];
4. Delay[1000]ms;
5. Send DiagBy[Physical]Data[3E 80];
6. Delay[<S3 - delta>]ms;（如 4900ms）
7. Send DiagBy[Physical]Data[22 F1 86];
```

#### Check 规则

**A. 3E 00：**
- 第 3 步：`Check DiagData[67 02]Within[50]ms;`
- 第 5 步：`Check DiagData[7E 00]Within[50]ms;`
- 第 7 步：`Check DiagData[62 F1 86 03]Within[50]ms;`（会话仍为 Extended）

**B. 3E 80：**
- 第 3 步：`Check DiagData[67 02]Within[50]ms;`
- 第 5 步：`Check No_Response Within[50]ms;`
- 第 7 步：`Check DiagData[62 F1 86 03]Within[50]ms;`（会话仍为 Extended）

#### 特殊规则

1. 验证 0x3E TesterPresent 能维持安全解锁状态
2. S3 - delta 使用边界值 4900ms（S3=5000ms 时）
3. 验证方式：延时后读取 DID F186（Active Diagnostic Session），确认仍为 Extended

---

### 分类 4: S3 Server Timer Test (APP)

#### 用例数量规则

**固定 4 条**，使用边界值测试

| 序号 | 场景 | 描述 |
|------|------|------|
| 1 | S3=4900ms（有效） + 3E 00 | 延时 4900ms 后发送 3E 00，会话保持 Extended |
| 2 | S3=5100ms（无效） + 3E 00 | 延时 5100ms 后发送 3E 00，会话回退 Default |
| 3 | S3=4900ms（有效） + 3E 80 | SPRMIB 版本，会话保持 Extended |
| 4 | S3=5100ms（无效） + 3E 80 | SPRMIB 版本，会话回退 Default |

#### 用例命名规则

1. `Valid equivalence class S3server=4900ms,0x3E service keeping extended Session 1Case-$3E`
2. `Invalid equivalence class S3server=5100ms,0x3E service does not keeping extended Session NegativeCase-$3E`
3. `Valid equivalence class S3server=4900ms,0x3E service with SPRMIB keeping extended Session 1Case-$3E`
4. `Invalid equivalence class S3server=5100ms,0x3E service with SPRMIB does not keeping extended Session NegativeCase-$3E`

#### 测试步骤模板

**场景 1: S3=4900ms + 3E 00**
```
1. Send DiagBy[Physical]Data[10 03];
2. Delay[1000]ms;
3. Send DiagBy[Physical]Data[3E 00];
4. Delay[4900]ms;
5. Send DiagBy[Physical]Data[22 F1 86];
```

**场景 2: S3=5100ms + 3E 00**
```
1. Send DiagBy[Physical]Data[10 03];
2. Delay[1000]ms;
3. Send DiagBy[Physical]Data[3E 00];
4. Delay[5100]ms;
5. Send DiagBy[Physical]Data[22 F1 86];
```

**场景 3/4: SPRMIB 版本，同上但用 3E 80**

#### Check 规则

**场景 1（有效）：**
- 第 3 步：`Check DiagData[7E 00]Within[50]ms;`
- 第 5 步：`Check DiagData[62 F1 86 03]Within[50]ms;`（仍为 Extended）

**场景 2（无效）：**
- 第 3 步：`Check DiagData[7E 00]Within[50]ms;`
- 第 5 步：`Check DiagData[62 F1 86 01]Within[50]ms;`（已回 Default）

**场景 3（SPRMIB 有效）：**
- 第 3 步：`Check No_Response Within[50]ms;`
- 第 5 步：`Check DiagData[62 F1 86 03]Within[50]ms;`

**场景 4（SPRMIB 无效）：**
- 第 3 步：`Check No_Response Within[50]ms;`
- 第 5 步：`Check DiagData[62 F1 86 01]Within[50]ms;`

#### 特殊规则

1. **使用边界值**：有效=4900ms（S3-100ms），无效=5100ms（S3+100ms）
2. S3 时间从参数表 `S3 Server Time` 读取，边界值按 S3±100ms 计算
3. F1 86 = Active Diagnostic Session DID：01=Default, 03=Extended
4. 0x3E 在延时前发送一次，然后等待延时结束验证会话状态

---

### 分类 5: ECU Reset Test (APP)

#### 用例数量规则

**固定 3 条**

| 复位方式 | 数量 |
|---------|------|
| Power Reset | 1 |
| Hardware Reset(11 01) | 1 |
| Session Switch（10 01） | 1 |

#### 用例命名规则

`<ResetType> the 0x3E service to keep the Session back from the extended Session to the default Session NegativeCase-$3E`

#### 测试步骤模板

**A. Power Reset：**
```
1. Send DiagBy[Physical]Data[10 03];
2. Delay[1000]ms;
3. Send DiagBy[Physical]Data[3E 00];
4. Delay[1000]ms;
5. Set Voltage[0]V;
6. Delay[1000]ms;
7. Set Voltage[12]V;
8. Delay[1000]ms;
9. Send DiagBy[Physical]Data[22 F1 86];
```

**B. Hardware Reset(11 01)：**
```
1. Send DiagBy[Physical]Data[10 03];
2. Delay[1000]ms;
3. Send DiagBy[Physical]Data[3E 00];
4. Delay[1000]ms;
5. Send DiagBy[Physical]Data[11 01];
6. Delay[1000]ms;
7. Send DiagBy[Physical]Data[22 F1 86];
```

**C. Session Switch（10 01）：**
```
1. Send DiagBy[Physical]Data[10 03];
2. Delay[1000]ms;
3. Send DiagBy[Physical]Data[3E 00];
4. Delay[1000]ms;
5. Send DiagBy[Physical]Data[10 01];
6. Delay[1000]ms;
7. Send DiagBy[Physical]Data[22 F1 86];
```

#### Check 规则

- 第 3 步：`Check DiagData[7E 00]Within[50]ms;`（3E 响应）
- 最后一步：`Check DiagData[62 F1 86 01]Within[50]ms;`（复位后回到 Default）

---

### 分类 6: Sub-function Traversal Test (APP)

#### 用例数量规则

**固定 1 条**

#### 用例命名规则

`0x3E service Subfunction traversal test NegativeCase-$3E`

#### 测试步骤模板

```
1. 进入支持的会话（Extended）
2. Send SubTraversalBy[Physical]Service[0x3E]Excluding[00 80]AndCheckResp[0x12];
```

#### Check 规则

- 第 2 步：不支持的子功能 → `7F 3E 12`

---

### 分类 7: Incorrect Diagnostic Command Test (APP)

#### 用例数量规则

**固定 2 条**

| 序号 | 错误类型 | 描述 |
|------|---------|------|
| 1 | SF_DL > 2 | 有效负载长度大于合法值 |
| 2 | SF_DL < 2 | 有效负载长度小于合法值 |

#### 用例命名规则

1. `Valid SF_DL=2, invalid SF_DL > 2, and those with invalid equivalence class SF_DL=3 NegativeCase-$3E`
2. `Valid SF_DL=2, invalid SF_DL < 2, and those with invalid equivalence class SF_DL=1 NegativeCase-$3E`

#### 测试步骤模板

**A. SF_DL > 2**
```
Send DiagBy[Physical]Data[3E 00]WithLen[3];
```

**B. SF_DL < 2**
```
Send DiagBy[Physical]Data[3E 00]WithLen[1];
```

#### Check 规则

| 错误类型 | Expected Output |
|---------|----------------|
| SF_DL > 2 | `Check DiagData[7F 3E 13]Within[50]ms;` |
| SF_DL < 2 | `Check DiagData[7F 3E 13]Within[50]ms;` |

---

### 分类 8: NRC Priority Test (APP)

#### 用例数量规则

**固定 2 条**

| 序号 | 场景 | 描述 |
|------|------|------|
| 1 | NRC 13 > 12 | 发送长度错误的 0x3E，验证返回 0x13 |
| 2 | NRC 12 | 发送不支持的子功能，验证返回 0x12 |

#### 用例命名规则

1. `NRC 13>12>22 NegativeCase-$3E`
2. `NRC 12 NegativeCase-$3E`

#### 测试步骤

**用例 1（NRC 13 优先）：**
```
1. Send DiagBy[Physical]Data[3E 01]WithLen[1];
```

**用例 2（NRC 12）：**
```
1. Send DiagBy[Physical]Data[3E 0A];
```

#### Check 规则

**用例 1：**
- `Check DiagData[7F 3E 13]Within[50]ms;`

**用例 2：**
- `Check DiagData[7F 3E 12]Within[50]ms;`

---

### 分类 9: Boot Domain Test

Boot 域生成与 APP 域完全相同结构的测试集，但有以下差异：

#### Boot 域差异

| 项目 | APP 域 | Boot 域 |
|------|--------|---------|
| 会话进入路径 | `10 03` 直接进入 Extended | `10 03 → 31 01 02 03 → 10 02` 进入 Programming |
| 安全等级 | L1（27 01 / 27 02） | LevelFBL（27 11 / 27 12） |
| S3 验证方式 | `22 F1 86`（读 DID） | `31 01 FF 01`（RoutineControl） |
| 会话验证值 | `62 F1 86 03`（Extended） | `71 01 FF 01 00`（正响应）或 `7F 31 31`（负响应） |

#### Boot 域子分类（与 APP 域完全对应）

Boot 域按以下顺序生成，每个子分类与 APP 域结构相同：

1. **Boot Physical - Session Layer**: Default/Programming/Extended 各 1 条
2. **Boot Physical - SPRMIB**: Default/Programming/Extended 各 1 条
3. **Boot Physical - Secure Access**: 使用 LevelFBL（27 11/12），在 Programming 会话下
4. **Boot Physical - S3 Timer**: 使用 `31 01 FF 01` 验证，边界值 4900ms/5100ms
5. **Boot Physical - ECU Reset**: Power Reset / HardReset / Session Switch
6. **Boot Physical - Sub-function Traversal**: 同 APP
7. **Boot Physical - Incorrect Command**: 同 APP（2 条 SF_DL）
8. **Boot Physical - NRC Priority**: 同 APP（2 条）
9. **Boot Functional**: Physical 的完整镜像，所有输出为 `Check No_Response Within[1000]ms;`

#### Boot Secure Access 测试步骤模板

```
1. Send DiagBy[Physical]Data[10 03];
2. Send DiagBy[Physical]Data[31 01 02 03];
3. Send DiagBy[Physical]Data[10 02];
4. Send DiagBy[Physical]Data[27 11]AndCheckResp[1];
5. Send Security Right KeyBy[Physical]Level[0x12];
6. Delay[1000]ms;
7. Send DiagBy[Physical]Data[3E 00];（或 3E 80）
```

#### Boot S3 Timer 测试步骤模板

```
1. Send DiagBy[Physical]Data[10 03];
2. Send DiagBy[Physical]Data[31 01 02 03];
3. Send DiagBy[Physical]Data[10 02];
4. Send DiagBy[Physical]Data[27 11]AndCheckResp[1];
5. Send Security Right KeyBy[Physical]Level[0x12];
6. Delay[1000]ms;
7. Send DiagBy[Physical]Data[3E 00];（或 3E 80）
8. Delay[4900]ms;（或 5100ms）
9. Send DiagBy[Physical]Data[31 01 FF 01];
```

#### Boot S3 Timer Check 规则

**有效（4900ms）：**
- 第 9 步：`Check DiagData[71 01 FF 01 00]Within[50]ms;`（仍在 Programming）

**无效（5100ms）：**
- 第 9 步：`Check DiagData[7F 31 31]Within[50]ms;`（已退出 Programming）

---

## 会话进入标准路径

| 目标会话 | APP 域标准进入步骤 | Boot 域标准进入步骤 |
|---------|-------------------|-------------------|
| Default（0x01） | `Send DiagBy[Physical]Data[10 01];` | `Send DiagBy[Physical]Data[10 01];` |
| Extended（0x03） | `Send DiagBy[Physical]Data[10 03];` | `Send DiagBy[Physical]Data[10 03];` |
| Programming（0x02） | `10 03 → 31 01 02 03 → 10 02` | `10 03 → 31 01 02 03 → 10 02` |

---

## 生成注意事项

1. **Case ID 不可重复**，物理寻址 `Diag_0x3E_Phy_001` 起递增，功能寻址 `Diag_0x3E_Fun_001` 起递增
2. **编号从 001 开始**，顺序为：APP Physical → APP Functional → Boot Physical → Boot Functional
3. **0x3E 通常在 Default、Extended 和 Programming 会话下都支持**
4. **S3 时间从参数表读取**，边界值按 S3±100ms 计算（如 S3=5000ms → 有效 4900ms，无效 5100ms）
5. **F1 86 DID 用于 APP 域读取当前会话号**：01=Default, 03=Extended
6. **Boot 域使用 `31 01 FF 01` 验证会话状态**：正响应=71 01 FF 01 00，负响应=7F 31 31
7. **Boot 域安全等级为 LevelFBL（27 11/27 12）**，不同于 APP 域的 L1（27 01/27 02）
8. **SPRMIB (3E 80) 无响应但仍刷新 S3**
9. **输出格式严格按照 Case ID / Case名称 / 测试步骤 / 预期输出 的固定模板**

---

## 分类汇总

| 分类 | 描述 | APP Physical | APP Functional | Boot Physical | Boot Functional |
|------|------|-------------|---------------|--------------|----------------|
| 1. Session Layer | 各会话测试 | 3 | 3 | 3 | 3 |
| 2. SPRMIB | 各会话 SPRMIB | 3 | 3 | 3 | 3 |
| 3. Secure Access | 维持 0x27 解锁 | 2 | 2 | 2 | 2 |
| 4. S3 Timer | 边界值测试 | 4 | 4 | 4 | 4 |
| 5. ECU Reset | 复位后状态 | 3 | 3 | 3 | 3 |
| 6. Sub Traversal | 子功能遍历 | 1 | 1 | 1 | 1 |
| 7. Incorrect Command | SF_DL 错误 | 2 | 2 | 2 | 2 |
| 8. NRC Priority | NRC 优先级 | 2 | - | 2 | - |
| **小计** | | **20** | **18** | **20** | **18** |
| **总计** | **76 条** | | | | |
