# Service 0x11 ECUReset — 用例生成规则

## 服务概述

- **Service ID**: 0x11
- **Service Name**: ECUReset
- **正响应 SID**: 0x51（0x11 + 0x40）
- **负响应格式**: `7F 11 <NRC>`
- **子功能**: 通常包含 01（HardReset）、02（KeyOffOnReset）、03（SoftReset），具体以参数表为准
- **关键特性**: 先回正响应，再执行复位；复位期间 ECU 不响应其它请求

### 正响应格式

- 若 `reset_time Support = N`：`51 <Subfunction>`
- 若 `reset_time Support = Y`：`51 <Subfunction> <ResetTime_H> <ResetTime_L>`
- `reset_time` 是否支持从参数表 `1.Basic Diagnostic Infomation -> $11 Timing parameters` 读取

### 典型 NRC

| NRC  | 含义 | 触发条件 |
|------|------|---------|
| 0x12 | Subfunction Not Supported | 发送了 0x11 不支持的子功能 |
| 0x13 | Incorrect Message Length Or Invalid Format | 报文长度错误（WithLen）或 DLC 异常 |
| 0x22 | Conditions Not Correct | 前置条件不满足 |
| 0x7E | Subfunction Not Supported In Active Session | 该子功能在当前会话下不支持 |
| 0x7F | Service Not Supported In Active Session | 当前会话下整体不支持 0x11 服务（客户口径） |

---

## 整体结构要求

每个软件域（App / Boot）每种寻址方式（Physical / Functional）必须独立生成完整用例集。

生成顺序：
1. **App Physical** — 标题 `1.Application Service_Physical Addressing`
2. **App Functional** — 标题 `2.Application Service_Functional Addressing`（仅当 Functional=Y）
3. **Boot Physical** — 标题 `3.Boot Service_Physical Addressing`
4. **Boot Functional** — 标题 `4.Boot Service_Functional Addressing`（仅当 Functional=Y）

每组内部包含以下分类（按顺序），每个分类使用 `## N.N` 作为标题（如 `## 1.1 Session Layer Test`）：
1. Session Layer Test
2. SPRMIB Test
3. Secure Access Test（即使无安全限制也必须生成验证用例）
4. Reset Effect Test（客户扩展）
5. Sub-function Traversal Test
6. Incorrect Diagnostic Command Test
7. NRC Priority Test（仅 Physical 寻址需要）
8. Functional Addressing Test（仅当 Functional 不支持时）

### 输出格式要求

1. **顶级标题使用 `#`**：如 `# 1. Application Service_Physical Addressing`、`# 2. Application Service_Functional Addressing`、`# 3. Boot Service_Physical Addressing`、`# 4. Boot Service_Functional Addressing`
2. **分类标题使用 `##`**：如 `## 1.1 Session Layer Test`、`## 1.2 SPRMIB Test`、`## 1.3 Secure Access Test` 等
3. **各大组之间用 `---` 分隔**
4. **无符合条件的用例时使用 `>` 引用**：如 `> App 域 0x11 所有子功能... 无符合条件的用例。`
5. **输出格式严格为 pipe table**，列顺序：`| Case ID | Case名称 | 测试步骤 | 预期输出 |`
6. **步骤中换行使用 `<br>` 标记**，不用 `\n`
7. **不要生成任何"参数提取结果"或"分析"段落**，直接输出测试用例表格

---

### 分类 1: Session Layer Test


#### 用例数量规则

必须覆盖**当前域的所有会话 × 所有子功能的完整交叉组合**（含全局不支持的子功能）。

- 对每个 (会话, 子功能) 组合：
  - 该会话支持该子功能 → 正向 case
  - 该会话不支持该子功能，但子功能全局存在 → 负向 case（NRC 0x7E）
  - 子功能全局不支持（Support=N）→ 也生成负向 case（NRC 0x12）
- **总数 = 可达会话数 × 子功能总数（含全局不支持的）**

#### 用例命名规则

- 正向：`<CurrentSessionName> Session support the 0x11 service 0x<Sub> subfunction`
  - 示例：`Extended Session support the 0x11 service 0x01 subfunction`
- 负向（会话不支持）：`<CurrentSessionName> Session nonsupport 0x11 services`
  - 示例：`Default Session nonsupport 0x11 services`
- 负向（子功能不支持）：`0x11 service nonsupport 0x<Sub> subfunction`
  - 示例：`0x11 service nonsupport 0x02 subfunction`

#### 测试步骤模板

**A. 当前会话不支持 0x11 服务（负向）**
```
1. 进入 <CurrentSessionNotSupport>（通常为 Default）
2. Send DiagBy[Physical]Data[11 <RepSupportedSub>];
```

**B. 支持子功能正向**
```
1. 进入 <CurrentSessionSupport>（通常为 Extended）
2. Send DiagBy[Physical]Data[11 <SupportSub>];
3. Delay[1000]ms;
```

**C. 子功能不支持（负向）**
```
1. 进入 <CurrentSessionSupport>（通常为 Extended）
2. Send DiagBy[Physical]Data[11 <UnsupportedSub>];
```

#### Check 规则

**A. 当前会话不支持服务：**
- `Check DiagData[7F 11 7F]Within[50]ms;`
- 注意：此处 NRC 使用 0x7F 而非 0x7E，为客户当前模板口径

**B. 支持子功能正向：**
- 若 reset_time Support = N：`Check DiagData[51 <Sub>]Within[50]ms;`
- 若 reset_time Support = Y：`Check DiagData[51 <Sub> <ResetTime_H> <ResetTime_L>]Within[50]ms;`

**C. 子功能不支持：**
- `Check DiagData[7F 11 12]Within[50]ms;`

#### 特殊规则

1. 0x11 先回正响应，再执行复位
2. Delay[500]ms 或 Delay[1000]ms 只用于等待 ECU 复位稳定，不单独写 check
3. 默认优先在 Extended 会话下做正向验证
4. 全局不支持的子功能不在 Session Layer 中出用例，放到 Sub-function Traversal Test

---

### 分类 2: SPRMIB Test


#### 用例数量规则

必须覆盖**所有会话 × 所有子功能的 SPRMIB 变体**（含 SPRMIB=N 和全局不支持的子功能）。

- 子功能支持 + SPRMIB=Y + 正向成功 → No_Response
- 子功能支持 + SPRMIB=N → 按原子子功能处理，正常返回响应或 NRC
- 子功能不支持（全局）→ NRC 0x12
- 会话不支持该子功能 → NRC 0x7E

**总数 = Session Layer 用例数**（一一对应）

#### 用例命名规则

在 Session Layer 对应名称后追加 `with SPRMIB`
- 示例：`Extended Session support the 0x11 service 0x01 subfunction with SPRMIB`

#### 测试步骤模板

在 Session Layer 同名 case 基础上：
1. 将最终请求 `11 <Sub>` 改为 `11 <0x80 + Sub>`
   - `11 01` → `11 81`
   - `11 02` → `11 82`
   - `11 03` → `11 83`
2. **必须追加复位后状态确认步骤**（因为正向响应被抑制，需额外验证复位生效）

正向完整步骤示例：
```
1. 进入 Extended 会话
2. Send DiagBy[Physical]Data[11 81];
3. Delay[1000]ms;
4. Send DiagBy[Physical]Data[22 F1 86];
```

#### Check 规则

**若原场景正向成功：**
- 第 2 步：`Check No_Response Within[1000]ms;`
- 第 4 步：`Check DiagData[62 F1 86 01]Within[50]ms;`（确认复位后回到默认会话）

**若原场景负向：**
- 仍返回负响应，规则同 Session Layer
- 会话不支持：`7F 11 7F`
- 子功能不支持：`7F 11 12`

#### 特殊规则

1. 正向 SPRMIB 场景必须追加 `22 F1 86` 状态确认，否则无法证明请求生效
2. Delay 步骤不写 check
3. No_Response 只适用于成功且支持 SPRMIB 的场景

---

### 分类 3: Secure Access Test


#### 用例数量规则

- `Nsecure11` = 需要先解锁才允许执行的 0x11 支持子功能数
- 从参数表 `Access Level` 字段读取安全等级
- **总数 = Nsecure11**
- **始终生成**：即使参数表显示无安全限制（Level0），也要生成用例验证锁定状态下服务可用性

#### 用例命名规则

`Security access Lx unlock supports 0x11 service 0x<Sub> subfunction`
- 示例：`Security access L2 unlock supports 0x11 service 0x01 subfunction`

#### 测试步骤模板

```
1. 进入允许安全访问的会话（通常 Extended）
2. Send DiagBy[Physical]Data[27 <SeedSub>]AndCheckResp[PostiveResponse];
3. Send Security Right KeyBy[Physical]Level[<KeySub>];
4. Send DiagBy[Physical]Data[11 <Sub>];
5. Delay[1000]ms;
```

#### Check 规则

- 第 1 步：`Check DiagData[50 03 ...]Within[50]ms;`
- 第 2 步：不单独写 Expected Output（AndCheckResp 已内含检查）
- 第 3 步：`Check DiagData[67 <KeySub>]Within[50]ms;`
- 第 4 步：
  - reset_time Support = N：`Check DiagData[51 <Sub>]Within[50]ms;`
  - reset_time Support = Y：`Check DiagData[51 <Sub> <ResetTime_H> <ResetTime_L>]Within[50]ms;`
- 第 5 步：Delay 不写 check

#### 特殊规则

1. 安全等级不写死，必须从参数表所在软件域的 Access Level 读取
2. SeedSub/KeySub 对应关系：L2 → 27 03/27 04，L4 → 27 07/27 08，其它等级按参数表映射
3. 安全访问步骤统一使用物理寻址

---

### 分类 4: Reset Effect Test（客户扩展）

> 此分类为客户企业内控项，验证 0x11 执行后 ECU 相关运行状态是否被 reset 回初始值。

#### 用例数量规则

设 `Ns` = 支持并可正向执行的 0x11 reset 子功能数，则：

| 子类 | 数量 | 条件 |
|------|------|------|
| Service Reset | Ns | 始终生成 |
| Security Access Reset | Ns | 安全访问存在时生成 |
| Communication Control State Reset | Ns | 0x28 服务支持时生成 |
| Fault Control State Reset | Ns | 0x85/0x14/0x19 支持时生成 |

**总数 = Ns × (1 + I(sec) + I(comm) + I(fault))**

#### 命名规则

- Service Reset：`0x11 Service 0x<Sub> subfunction non-Default Session to Default Session`
- Security Access Reset：`0x11 Service 0x<Sub> subfunction Security access reset`
- Communication Control State Reset：`0x11 Service 0x<Sub> subfunction communication control state reset`
- Fault Control State Reset：`0x11 Service 0x<Sub> subfunction fault control state reset`

#### 各子类步骤与 Check

##### A. Service Reset

**步骤：**
```
1. 进入非默认会话（Extended）
2. Send DiagBy[Physical]Data[11 <Sub>];
3. Delay[1000]ms;
4. Send DiagBy[Physical]Data[22 F1 86];
```

**Check：**
- 第 2 步：`Check DiagData[51 <Sub>]Within[50]ms;`
- 第 4 步：`Check DiagData[62 F1 86 01]Within[50]ms;`

##### B. Security Access Reset

**步骤：**
```
1. 进入允许安全访问的会话（Extended）
2. Send DiagBy[Physical]Data[27 <SeedSub>]AndCheckResp[PostiveResponse];
3. Send Security Right KeyBy[Physical]Level[<KeySub>];
4. Send DiagBy[Physical]Data[11 <Sub>];
5. Delay[1000]ms;
6. Send DiagBy[Physical]Data[22 F1 86];
7. Send DiagBy[Physical]Data[27 <SeedSub>];
```

**Check：**
- 第 3 步：`Check DiagData[67 <KeySub>]Within[50]ms;`
- 第 4 步：`Check DiagData[51 <Sub>]Within[50]ms;`
- 第 6 步：`Check DiagData[62 F1 86 01]Within[50]ms;`
- 第 7 步：`Check DiagData[7F 27 7F]Within[50]ms;`（验证已恢复锁定态）

##### C. Communication Control State Reset

**步骤：**
```
1. 进入非默认会话（Extended）
2. Send DiagBy[Physical]Data[28 01 01];
3. Check MsgInexist[<MonitoredMsgId>];
4. Send DiagBy[Physical]Data[11 <Sub>];
5. Delay[1000]ms;
6. Check MsgExist[<MonitoredMsgId>];
7. Send DiagBy[Physical]Data[22 F1 86];
```

**Check：**
- 第 2 步：`Check DiagData[68 01]Within[50]ms;`
- 第 4 步：`Check DiagData[51 <Sub>]Within[50]ms;`
- 第 7 步：`Check DiagData[62 F1 86 01]Within[50]ms;`
- MonitoredMsgId 默认使用 0x21F（可配置）

##### D. Fault Control State Reset

**步骤：**
```
1. 进入非默认会话（Extended）
2. Send DiagBy[Physical]Data[85 02 FF FF FF];
3. Send DiagBy[Physical]Data[14 FF FF FF];
4. Set Voltage[6.8]V;
5. Delay[3000]ms;
6. Send DiagBy[Physical]Data[19 02 FF];
7. Send DiagBy[Physical]Data[11 <Sub>];
8. Delay[1000]ms;
9. Send DiagBy[Physical]Data[19 02 FF];
10. Set Voltage[12]V;
```

**Check：**
- 第 2 步：`Check DiagData[C5 02]Within[50]ms;`
- 第 3 步：`Check DiagData[54]Within[50]ms;`
- 第 6 步：检查复位前 DTC 状态
- 第 7 步：`Check DiagData[51 <Sub>]Within[50]ms;`
- 第 9 步：检查复位后 fault control 状态是否恢复

> 此子类为强客户化模板，严格按 K 列或项目确认脚本生成。

---

### 分类 5: Sub-function Traversal Test


#### 用例数量规则

**固定 3 条**，覆盖所有可达会话：
1. Default Session — 遍历非法子功能
2. Programming Session — 遍历非法子功能
3. Extended Session — 遍历非法子功能

#### 用例命名规则

`Subfunction traversal test in the <CurrentSessionName> Session`

#### 测试步骤模板

```
1. 进入 <CurrentSession>
2. Send SubTraversalBy[Physical]Service[0x11]Excluding[<SupportSubList>]AndCheckResp[<RespCode>];
```

其中：
- `<SupportSubList>` = 支持的子功能 + 支持 SPRMIB 的镜像子功能
  - 示例：若支持 01、03 且都支持 SPRMIB，则 Excluding 填 `01 03 81 83`

#### Check 规则

- 第 1 步：检查进入当前会话的正响应
- 第 2 步：不单独写 Expected Output（AndCheckResp 已内含检查）
  - Default 场景：`<RespCode>` 取 `0x7E`
  - Extended 场景：`<RespCode>` 取 `0x12`

#### 特殊规则

1. Traversal 要区分"服务在当前会话是否有效"与"子功能本身是否有效"
2. 不要把 Session Layer 中已覆盖的"支持但当前会话不允许"的子功能混到 traversal

---

### 分类 6: Incorrect Diagnostic Command Test


#### 用例数量规则

**固定 4 条 / 每种支持的寻址方式**

| 序号 | 错误类型 | 描述 |
|------|---------|------|
| 1 | DLC < 8 | CAN 帧 DLC 不足 8 字节 |
| 2 | DLC > 8 | CAN 帧 DLC 超过 8 字节 |
| 3 | SF_DL > 2 | 有效负载长度大于合法值 |
| 4 | SF_DL < 2 | 有效负载长度小于合法值 |

#### 用例命名规则

1. `When a diagnostic message with DLC < 8 is sent, ECU does not respond`
2. `When a diagnostic message with DLC > 8 is sent, ECU responds normally`
3. `Valid SF_DL=2, invalid SF_DL > 2 triggers NRC 0x13`
4. `Valid SF_DL=2, invalid SF_DL < 2 triggers NRC 0x13`

#### 测试步骤模板

**前置步骤（所有 4 条共用）：**
进入支持 0x11 的当前会话（通常 Extended）

**A. DLC < 8**
```
Send Msg[<ReqCANID>]Data[02 11 <RepSub>]WithDLC[7];
```

**B. DLC > 8**
```
Send Msg[<ReqCANID>]Data[02 11 <RepSub>]WithDLC[9];
```

**C. SF_DL > 2**
```
Send DiagBy[Physical]Data[11 <RepSub>]WithLen[3];
```

**D. SF_DL < 2**
```
Send DiagBy[Physical]Data[11 <RepSub>]WithLen[1];
```

其中：
- `<RepSub>` 优先选当前会话下可执行的支持子功能，默认优先 `01`
- `<ReqCANID>` 物理寻址用 `Diagnostic Req CANID`，功能寻址用 `Diagnostic Functional Req CANID`

#### Check 规则

| 错误类型 | Expected Output |
|---------|----------------|
| DLC < 8 | `Check No_Response Within[1000]ms;` |
| DLC > 8 | `Check DiagData[51 <RepSub> [resetTime]]Within[50]ms;` |
| SF_DL > 2 | `Check DiagData[7F 11 13]Within[50]ms;` |
| SF_DL < 2 | `Check DiagData[7F 11 13]Within[50]ms;` |

#### 特殊规则

1. 0x11 的合法 SF_DL 为 2 字节数据负载（SID + Subfunction）
2. DLC 错误测试使用 `Send Msg...WithDLC[...]`
3. SF_DL 错误测试使用 `Send DiagBy...WithLen[...]`

---

### 分类 7: NRC Priority Test

#### 用例数量规则

**仅 Physical 寻址生成，固定 1 条**。

#### 用例命名规则

`NRC <优先级链>`

示例：`NRC 13>12>22`

#### 测试步骤模板

```
1. 进入支持 0x11 的会话（如 Extended）
2. Send DiagBy[Physical]Data[11 <RepSub>]WithLen[1];
3. Delay[2000]ms;
```

#### Check 规则

- `Check DiagData[7F 11 13]Within[50]ms;`
- NRC 优先级链从参数表读取（如 `13>12>22`），验证最高优先级 NRC

#### 特殊规则

1. NRC Priority 仅在 Physical 寻址下生成，Functional 不需要
2. 使用 WithLen 制造长度错误来触发 NRC 0x13

---

### 分类 8: Functional Addressing Test（客户扩展）

#### 用例数量规则

**仅当参数表 `Functional Request = 不支持` 时生成，固定 3 条：**
- 对标准子功能 {01, 02, 03} 各 1 条

若 `Functional Request = 支持`，则不使用本分类，改为像 0x10 一样复制 Session/SPRMIB/Traversal/Incorrect 的 Functional 版本。

#### 用例命名规则

`0x11 Service nonsupport functional addressing subfunction 0x<Sub>`
- 示例：`0x11 Service nonsupport functional addressing subfunction 0x01`

#### 测试步骤模板

```
1. 进入 Extended 会话（使用 Physical）
2. Send DiagBy[Function]Data[11 <Sub>];
3. Delay[1000]ms;
```

#### Check 规则（客户最新口径）

| 子功能 | Expected Output |
|--------|----------------|
| 11 01 | `Check No_Response Within[1000]ms;` |
| 11 02 | `Check DiagData[7F 11 12]Within[50]ms;` |
| 11 03 | `Check No_Response Within[1000]ms;` |

> 注意：`11 02` 的 NRC 报文格式必须写成 `7F 11 12`，不能写成 `7F 12 12`。

#### 特殊规则

1. 0x11 功能寻址所有产品都不支持（客户规则）
2. 11 01 和 11 03 无响应，11 02 返回 NRC 0x12
3. 如果后续业务决定功能寻址一律 No_Response，只需把 3 条统一改成无响应即可

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
1. 将所有 Physical 用例复制一份（Session Layer + SPRMIB + Secure Access + Reset Effect + Traversal + Incorrect Diag Command）
2. 发送函数中 `[Physical]` 改为 `[Function]`
3. Case ID 中 `Phy` 改为 `Fun`，编号重新从 001 开始
4. 安全访问步骤（0x27 seed/key）仍使用 Physical
5. 复位后验证步骤仍使用 Physical
6. **Functional 寻址下正向 0x11 hardReset 预期为 `No_Response`**
7. **Functional 寻址下不支持的子功能预期为 `No_Response Within[1000]ms;`**（不返回 NRC）
8. 不生成 NRC Priority Test（仅 Physical）

当 `Functional Request = 不支持` 时：
- 仅生成分类 7（Functional Addressing Test）的 3 条锁定行为验证用例

---

## BootLoader 域规则

当软件域为 BootLoader 时：
1. 从参数表 `Supported Session in BootLoader` 读取会话支持矩阵
2. 从参数表 BootLoader 部分读取 Access Level
3. 用例命名和分类标题加 Boot 标识：`--Boot Session`
4. 规则与 App 相同，仅参数来源不同
5. **Boot 域也必须生成 Functional 用例**（当 Functional=Y 时）
6. Boot 域安全访问使用对应的 Seed/Key（通常是 27 11/27 12 即 LevelFBL）

---

## 生成注意事项

1. **Case ID 不可重复**，物理寻址 `Diag_0x11_Phy_001` 起递增，功能寻址 `Diag_0x11_Fun_001` 起递增
2. **编号从 001 开始**，优先编写所有 Physical 用例，再编写 Functional 用例
3. **每个 Send 都要有对应 Check**，除以下豁免：
   - `Delay[...]ms` 不写 Check
   - 带 `AndCheckResp[...]` 的发送函数不单独写 Check
   - `Check MsgInexist[...]` / `Check MsgExist[...]` 本身就是检查，不再重复
4. **步骤和 Check 的编号必须对应**
5. **不可省略任何分类**，所有分类必须全部生成（条件不满足的标明"无符合条件的用例"）
6. **输出格式严格为 pipe table**，列顺序：`| Case ID | Case名称 | 测试步骤 | 预期输出 |`
7. **步骤中换行使用 `<br>` 标记**，不用 `\n`
8. **NRC 优先级链从参数表精确读取**，不要猜测
9. **不要生成任何"参数提取结果"或"分析"段落**，直接输出测试用例表格
10. **进入 Programming 会话前必须先执行 RoutineControl**（如 `31 01 02 03`），否则 ECU 可能拒绝进入 Programming

## Timing 参数提取规则

从参数表精确提取：
- P2 Server Max → 直接读取 ms 值，hex 编码公式：`P2ms / 1` → 转为 2 字节 hex
- P2* Server Max → hex 编码公式：`P2*ms / 10` → 转为 2 字节 hex
- 示例：P2=50ms → 50=0x0032 → `00 32`；P2*=5000ms → 500=0x01F4 → `01 F4`
- **正响应 Timing Bytes 用于 0x10 Session 切换响应**（`50 <Sub> 00 32 01 F4`），不直接用于 0x11 正响应

## 会话进入标准路径

| 目标会话 | 标准进入步骤 |
|---------|------------|
| Default（0x01） | `Send DiagBy[Physical]Data[10 01];` |
| Extended（0x03） | `Send DiagBy[Physical]Data[10 01];` → `Delay[1000]ms;` → `Send DiagBy[Physical]Data[10 03];` |
| Programming（0x02） | `Send DiagBy[Physical]Data[10 01];` → `Delay[1000]ms;` → `Send DiagBy[Physical]Data[10 03];` → `Send DiagBy[Physical]Data[31 01 02 03];` → `Send DiagBy[Physical]Data[10 02];` |

**重要**：进入 Programming 会话前必须先执行 RoutineControl（如 `31 01 02 03`）。
