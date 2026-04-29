## 0.1 输入字段读取口径（只针对 0x10 ）

#### `1.Basic Diagnostic Infomation`
用于生成公共参数：

- `Diagnostic Req CANID(only for CAN ECU)`：物理寻址错误帧测试使用
- `Diagnostic Functional Req CANID(only for CAN ECU)`：功能寻址错误帧测试使用
- `P2Server Max`：0x10 正响应中的 `P2Server_max`
- `P2*Server Max`：0x10 正响应中的 `P2*Server_max`
- `S3Server`：0x10 S3 超时测试使用
- `$11 Timing parameters -> reset_time Support / Byte Length / Unit`：0x11 正响应是否带 `resetTime` 参数

#### `2.Diagnostic Services`
用于生成 0x10 用例矩阵：

- `Service ID`
- `Service Name`
- `Subfunction`
- `Subfunction Name`
- `Hex Value`
- `Support`
- `SPRMIB`
- `Physical Request`
- `Functional Request`
- `Supported Session in App`
  - `Default 0x01`
  - `Programming 0x02`
  - `Extended 0x03`
  - `Access Level`
- `Supported Session in BootLoader`
  - `Default 0x01`
  - `Programming 0x02`
  - `Extended 0x03`
  - `Access Level`
- `Negative response codes`
只参考一个service id：

- `DiagnosticSessionControl_0x10`

生成结果重点字段：

- **D 列**：用例名称样式（Default Session to  Default Session PositiveCase-$10；Default Session to  Programming Session NegativeCase-$10）
- **I 列**：测试步骤写法（Send DiagBy[Physics]Data[10 01];Send DiagBy[Physics]Data[10 01];）
- **J 列**：预期输出写法（1.Check DiagData[50 01 00 32 00 C8]Within[50]ms;2.Check DiagData[50 01 00 32 00 C8]Within[50]ms;）

汽车电子函数接口定义：
用于确定 CAPL 风格函数接口的标准写法：

- `Send DiagBy[Physical]Data[...]`
- `Send DiagBy[Function]Data[...]`
- `Send Msg[...]Data[...]WithDLC[...]`
- `Check DiagData[...]Within[...]ms`
- `Check No_Response Within[...]ms`
- `Send Security Right KeyBy[...]Level[...]`
- `Send SubTraversalBy[...]Service[...]Excluding[...]AndCheckResp[...]`
- `Send DiagBy[...]Data[...]WithLen[...]`
- `Check MsgInexist[...]`
- `Check MsgExist[...]`

---

## 0.2 输出格式通用规则

### 0.2.1 Case ID 规则

统一采用：

- 物理寻址：`Diag_0x10_Phy_001`、`Diag_0x11_Phy_001`
- 功能寻址：`Diag_0x10_Fun_001`、`Diag_0x11_Fun_001`

规则：

- `Diag_`
- 服务号（如 `0x10`）
- 寻址方式（`Phy` / `Fun`）
- 三位流水号

### 0.2.2 Case 名称规则

#### 0x10
- Session：`Service 0x10 <CurrentSession> To <TargetSession>`
- SPRMIB：`Service 0x10 <CurrentSession> To <TargetSession> with SPRMIB`
- Secure Access：`Security access Lx unlock supports jumping to <TargetSession> Session`
- ECU Reset：`ECU <ResetType> reset Session returns to the Default Session`
- Traversal：`Subfunction traversal test in the <CurrentSession> Session`
- S3：`S3Server maintains...` / `S3Server returns...`
- Incorrect Command：`When a diagnostic message with DLC != 8` / `Valid SF_DL=2, invalid SF_DL != 2`

#### 0x11
- Session：`Service 0x11 <CurrentSession> supports/nonsupport <SubfunctionName>`
- SPRMIB：在 Session 名称后加 `with SPRMIB`
- Secure Access：`Security access Lx unlock supports 0x11 service <Subfunction>`
- Reset Effect：`0x11 Service <Subfunction> <ResetEffect>`
- Traversal：`Subfunction traversal test in the <CurrentSession> Session`
- Incorrect Command / Functional：`When a diagnostic message with DLC != 8` / `Valid SF_DL=2, invalid SF_DL != 2`

### 0.2.3 测试步骤与预期输出的编写原则

1. **每一个发送动作原则上都要有对应 check（Expected Output）。**
2. **以下两类步骤不单独写 Expected Output：**
   - `Delay[...]ms`
   - 已带 `AndCheckResp[...]` 的发送函数
3. **以下检查型步骤本身就是检查动作，不再在 Expected Output 中重复：**
   - `Check MsgInexist[...]`
   - `Check MsgExist[...]`
4. `Check DiagData[...]Within[50]ms` 为默认诊断响应检查写法。
5. `Check No_Response Within[1000]ms` 为默认“无响应”检查写法；若业务明确指定更长时间，按客户规则覆盖。
6. 0x10 正响应格式：
   - `50 <Subfunction> <P2ServerMax_H> <P2ServerMax_L> <P2*ServerMax_H> <P2*ServerMax_L>`
   - `50 serviceID 0x10 + 0x40`
7. 0x11 正响应格式：
   - 若 `reset_time Support = N`：`51 <Subfunction>`
   - 若 `reset_time Support = Y`：`51 <Subfunction> <ResetTime_H> <ResetTime_L>`
   - `51 serviceID 0x11 + 0x40`

---

## 0.3 协议与报文通用规则

### 0.3.1 0x10 正/负响应规则

- 正响应：`<service ID +40> + Subfunction + timing parameter`
- 负响应：`7F <service ID> <NRC>`

典型 NRC：

- `0x12`：Subfunction Not Supported
- `0x13`：Incorrect Message Length Or Invalid Format
- `0x22`：Conditions Not Correct
- `0x7E`：Subfunction Not Supported In Active Session

### 0.3.2 0x11 正/负响应规则

- 正响应：`<service ID +40> + Subfunction [+ resetTime]`
- 负响应：`7F <service ID> <NRC>`

典型 NRC：

- `0x12`：Subfunction Not Supported
- `0x13`：Incorrect Message Length Or Invalid Format
- `0x22`：Conditions Not Correct
- `0x7E`：Subfunction Not Supported In Active Session
- `0x7F`：Service Not Supported In Active Session（客户模板中用于“当前会话下整体不支持 0x11 服务”的口径）

### 0.3.3 SPRMIB 规则

- 子功能抑制位：`0x80 + 原子功能`
- 对 **执行成功** 的请求：
  - 若支持 SPRMIB，则 **抑制肯定响应**，检查 `No_Response`
- 对 **执行失败** 的请求：
  - 仍返回 **否定响应**


### 0.3.4 0x10 进入会话的标准准备路径

为了让自动生成器输出稳定、便于评审，进入当前会话建议统一使用如下规范路径：

- 进入 Default：`10 01`
- 进入 Extended：`10 01 -> Delay[1000]ms -> 10 03`
- 进入 Programming：`10 01 -> Delay[1000]ms -> 10 03 -> 10 02`

> 说明：这不是 ISO 唯一允许路径，沉淀出来的“标准建链路径”，便于统一生成。

### 0.3.5 安全访问解锁的标准写法

先根据 0x10 所在域读取 `Access Level`，再到 0x27 中取对应的 seed/key 对：

- `L2` 对应：`27 03 / 27 04`
- `L4` 对应：`27 07 / 27 08`
- 其他等级：按输入表Service ID 0x27 行映射，不写死

统一写法：

1. 先进入允许发种子的会话
2. `Send DiagBy[Physical]Data[27 <SeedSub>]AndCheckResp[PostiveResponse]`
3. `Send Security Right KeyBy[Physical]Level[<KeySub>]`
4. 再发送被测服务请求

> 说明：**安全访问步骤本身统一使用物理寻址**；只有被测 0x10 会话切换请求在功能寻址类 case 中改成 Function。

---

# 1. Service 0x10 DiagnosticSessionControl (8 类测试)

## 1.0 适用范围

0x10 的分类框架按 PDF 固定为 8 类：

1.1 Session Layer Test
1.2 SPRMIB Test
1.3 Secure Access Test
1.4 ECU Reset Test
1.5 Sub-function Traversal Test
1.6 S3 Server Timer Test
1.7 Incorrect Diagnostic Command Test
1.8 NRC Priority Test

### 寻址方式规则

若 `Functional Request` 支持，则在相同软件域下 **额外生成一份 Functional 寻址用例**；
若 `Functional Request` 不支持，则不生成 Functional 版。

> **注意**：Functional 寻址不是简单的 Physical 1:1 复制。部分类别的数量和行为在 Functional 下不同：
> - **S3 Timer**：Physical 1 条 vs Functional 2 条
> - **Incorrect Command**：Physical 2 条 vs Functional 2 条（数量相同但用不同 CAN ID）
> - **NRC Priority**：只在 Physical 下生成，Functional 不重复
> - **ECU Reset**：Physical 和 Functional 都生成，但 reset 触发和验证步骤统一用 Physical

### 软件域规则

**必须独立为每个软件域生成完整用例集。** 软件域按输入表区分：

- Application / App
- BootLoader / Boot / FBL

若输入表中同时包含 `ApplicationServices` 和 `BootServices` 两个 Sheet（或同一 Sheet 中包含 App 和 Boot 两段数据），则 **必须为两个域分别生成完整的 8 类测试用例**。两个域的子功能支持矩阵、会话权限、安全等级可能完全不同，不能复用。

> **示例**：若输入有 App 域（3 个子功能）和 Boot 域（3 个子功能），且 Physical 和 Functional 都支持，则生成结构为：
> ```
> 1. App Physical: 8 类用例
> 2. App Functional: 8 类用例（去除 NRC Priority）
> 3. Boot Physical: 8 类用例
> 4. Boot Functional: 8 类用例（去除 NRC Priority）
> ```

---

## 1.1 Session Layer Test


### 1.1.1 用例数量规则

**通用公式：**

- 设 `R` = 当前软件域下可达的“当前会话集合”
- 设 `T` = 当前软件域下 0x10 支持的目标子功能集合（01/02/03）
- 则 **Session Layer Test 数量 = `|R| × |T|`**

#### 最少条数
- **1 条**
- 场景：只有 `10 01` 被支持，且只验证 Default -> Default

#### 最多条数
- **9 条 / 每个软件域 / 每种支持的寻址方式**
- 场景：`01/02/03` 全支持，且 Default / Extended / Programming 都可作为当前会话

### 1.1.2 用例命名规则

`Service 0x10 <CurrentSessionName> To <TargetSessionName>`

例如：

- `Service 0x10 Default To Default`
- `Service 0x10 Extended To Programming`
- `Service 0x10 Programming To Extended`

### 1.1.3 测试步骤模板

#### A. 正向类（目标子功能在当前会话下允许）

**步骤模板：**

1. 进入 `<CurrentSession>`
2. 发送 `Send DiagBy[<Addr>]Data[10 <TargetSub>]`

其中：

- `<Addr>` = `Physical` 或 `Function`
- `<TargetSub>` ∈ `01 / 02 / 03`

**当前会话进入步骤建议：**

- Current = Default  
  `1.Send DiagBy[<Addr>]Data[10 01];`

- Current = Extended  
  `1.Send DiagBy[<Addr>]Data[10 01];`  
  `2.Delay[1000]ms;`  
  `3.Send DiagBy[<Addr>]Data[10 03];`

- Current = Programming  
  `1.Send DiagBy[<Addr>]Data[10 01];`  
  `2.Delay[1000]ms;`  
  `3.Send DiagBy[<Addr>]Data[10 03];`  
  `4.Send DiagBy[<Addr>]Data[10 02];`

然后再发：

- `5.Send DiagBy[<Addr>]Data[10 <TargetSub>];`

### 1.1.4 Check 规则

#### 进入当前会话的 check
- `10 01` -> `Check DiagData[50 01 <P2> <P2*>]Within[50]ms;`
- `10 03` -> `Check DiagData[50 03 <P2> <P2*>]Within[50]ms;`
- `10 02` -> `Check DiagData[50 02 <P2> <P2*>]Within[50]ms;`

其中：

- `<P2>` = 从 `P2Server Max` 转换成 2 字节十六进制
- `<P2*>` = 从 `P2*Server Max / 10` 转换成 2 字节十六进制

#### 目标请求的 check
- 若允许切换：`Check DiagData[50 <TargetSub> <P2> <P2*>]Within[50]ms;`
- 若目标子功能在该当前会话下不支持：`Check DiagData[7F 10 7E]Within[50]ms;`
- 若目标子功能因前置条件不满足（例如编程会话前置条件未满足）：`Check DiagData[7F 10 22]Within[50]ms;`

### 1.1.5 特殊规则

1. **全局不支持的子功能** 不在 Session Layer 里出用例，而是放到 `1.5 Sub-function Traversal Test`。
2. 功能寻址版的 0x10 Session Layer，**原则上和物理寻址预期一致，只改发送寻址方式**。
3. 当前模板里个别功能寻址负向 case 写成了 `No_Response`，本文不沿用；按 PDF+K 的总体规则，若 `Functional Request` 对 0x10 是支持的，则负向应答也应正常检查 NRC。

---

## 1.2 SPRMIB Test


### 1.2.1 用例数量规则

**通用公式：**

- 设 `R` = 当前软件域可达的当前会话集合
- 设 `T` = 当前软件域 0x10 所有支持的子功能集合（**不区分 SPRMIB 是否支持**）
- 则 **SPRMIB Test 数量 = `|R| × |T|`**

> **关键规则**：SPRMIB 测试必须覆盖 **所有子功能**，不仅仅是 `SPRMIB=Y` 的子功能。
> - `SPRMIB=Y` 的子功能：发送 `0x80 + Sub`，预期响应被抑制（No_Response）
> - `SPRMIB=N` 的子功能：发送 `0x80 + Sub`，此时 suppress bit 不被支持，ECU 可能按原子功能处理或返回 NRC；按输入表 `Negative response codes` 判定预期响应

#### 最少条数
- **0 条**
- 场景：该服务没有任何支持的子功能

#### 最多条数
- **9 条 / 每个软件域 / 每种支持的寻址方式**
- 即 `3 个当前会话 × 3 个子功能 = 9 条`

### 1.2.2 用例命名规则

`Service 0x10 <CurrentSessionName> To <TargetSessionName> with SPRMIB`

### 1.2.3 测试步骤模板

在 Session Layer 的同名 case 基础上，把最终请求改为：

- `10 <0x80 + TargetSub>`

例如：

- `10 01` -> `10 81`
- `10 02` -> `10 82`
- `10 03` -> `10 83`

### 1.2.4 Check 规则

- 若原始请求应为正向执行成功：
  - `Check No_Response Within[1000]ms;`
- 若原始请求本应为负向：
  - 仍检查对应 NRC
  - 会话不支持：`7F 10 7E`
  - 前置条件不满足：`7F 10 22`
  - 其他非法子功能：`7F 10 12`

### 1.2.5 特殊规则

1. `No_Response` 只适用于 **成功且支持 SPRMIB 的场景**。
2. `Delay` 不写 check。
3. 带 `AndCheckResp[...]` 的步骤不再单列 Expected Output。
4. 若客户后续明确某一特定寻址方式“负向也统一无响应”，则再做客户化覆盖；当前规则不默认这样做。

---

## 1.3 Secure Access Test


### 1.3.1 用例数量规则

**通用公式：**

- 设 `Tu` = 需要先解锁才能进入/验证的目标会话集合
- 则 **Secure Access Test 数量 = `|Tu|`**

#### 最少条数
- **0 条**
- 场景：该软件域下 0x10 不受安全等级限制

#### 最多条数
- **3 条 / 每个软件域 / 每种支持的寻址方式**
- 对应跳转到 `Default / Programming / Extended`

### 1.3.2 用例命名规则

`Security access Lx unlock supports jumping to <TargetSessionName> Session`

### 1.3.3 测试步骤模板

1. 进入允许安全访问 seed 请求的当前会话
2. `Send DiagBy[Physical]Data[27 <SeedSub>]AndCheckResp[PostiveResponse];`
3. `Send Security Right KeyBy[Physical]Level[<KeySub>];`
4. `Send DiagBy[<Addr>]Data[10 <TargetSub>];`

#### 推荐前置会话
- App/L2：先入 `10 03`
- Boot/L4：先入 `10 02` 或按 0x27 规则进入编程会话后再发种子

### 1.3.4 Check 规则

- 进入前置会话：检查 `50 03...` 或 `50 02...`
- 第 2 步不单独写 Expected Output（因 `AndCheckResp` 已内含检查）
- 第 3 步：`Check DiagData[67 <KeySub>]Within[50]ms;`
- 第 4 步：
  - 成功切换：`Check DiagData[50 <TargetSub> <P2> <P2*>]Within[50]ms;`
  - 若解锁后仍不允许：按输入表 `Negative response codes` 字段取值检查

### 1.3.5 特殊规则

1. 安全等级 **不写死成 L2**，必须从输入表当前软件域 `Access Level` 读取。
2. 如果某目标会话本身不支持，则不生成对应 Secure Access case。
3. 功能寻址类 0x10 Secure Access 用例中，**0x27 种子/密钥过程仍使用 Physical**；只有被测 `10 xx` 改成 `Function`。

---

## 1.4 ECU Reset Test

### 1.4.1 用例数量规则

**通用公式：**

- 固定包含：`Power Reset` 1 条
- 再加：0x11 中所有存在的子功能类型 `Nreset11`（**不论该子功能 Support 字段是否为 Y**）
- 则 **ECU Reset Test 数量 = `1 + Nreset11`**

> **关键规则**：即使某个 0x11 子功能在当前会话下 `Support=N`，ECU Reset Test 仍然要包含该子功能的 reset 测试。因为测试目的是验证 0x10 会话状态在 reset 后是否回到 Default，不是验证 0x11 自身。

#### 最少条数
- **1 条**
- 只有电源重启验证

#### 最多条数
- **4 条**
- 典型场景：`Power Reset + HardReset + KeyOffOnReset + SoftReset`

> 当前客户模板显式落了 `Power Reset / Hardware Reset / Software Reset` 三类（KeyOffOn 视项目而定）。

### 1.4.2 用例命名规则

`ECU <ResetType> reset Session returns to the Default Session`

### 1.4.3 测试步骤模板

#### A. Power Reset
1. 进入非默认会话（建议 `10 03`）
2. `Set Voltage[0]V;`
3. `Delay[3000]ms;`
4. `Set Voltage[12]V;`
5. `Delay[3000]ms;`
6. `Send DiagBy[Physical]Data[22 F1 86];`

#### B. 0x11 Hardware / Soft / KeyOffOn Reset
1. 进入非默认会话（建议 `10 03`）
2. `Send DiagBy[Physical]Data[11 <ResetSub>];`
3. `Delay[1000]ms;`
4. `Send DiagBy[Physical]Data[22 F1 86];`

### 1.4.4 Check 规则

- 第 1 步进入非默认会话：`Check DiagData[50 03 ...]Within[50]ms;`
- 0x11 reset 请求：
  - `11 01` -> `Check DiagData[51 01]Within[50]ms;`
  - `11 02` -> `Check DiagData[51 02 ...]Within[50]ms;`（若支持）
  - `11 03` -> `Check DiagData[51 03]Within[50]ms;`
- reset 后读 DID F186：
  - `Check DiagData[62 F1 86 01]Within[50]ms;`

### 1.4.5 特殊规则

1. **Power Reset 为客户强制保留项。**
2. 用例目的不是验证 0x11 自身，而是验证 **0x10 所在状态在 reset 后回到 Default**。
3. 功能寻址版 0x10 的 Reset Test 中：
   - 进入非默认会话的 `10 xx` 可用 `Function`
   - 复位触发与复位后验证仍使用 `Physical`

---

## 1.5 Sub-function Traversal Test


### 1.5.1 用例数量规则

**通用公式：**

- 设 `A` = 需要覆盖的当前会话锚点集合
- 则 **Traversal 用例数 = `|A|`**

#### 最少条数
- **1 条**

#### 最多条数
- **3 条**
- 覆盖 `Default / Extended / Programming` 三种当前会话语义

### 1.5.2 用例命名规则

`Subfunction traversal test in the <CurrentSessionName> Session`

### 1.5.3 测试步骤模板

1. 进入 `<CurrentSession>`
2. `Send SubTraversalBy[<Addr>]Service[0x10]Excluding[<SupportSubList>]AndCheckResp[<RespCode>];`

其中：

- `<SupportSubList>` = 当前软件域下所有支持的 0x10 子功能 + 对应支持的 SPRMIB 子功能
  - 例如：`01 02 03 81 82 83`
- `<RespCode>` 通常取 `0x12`

### 1.5.4 Check 规则

- 第 1 步：检查进入当前会话的正响应
- 第 2 步：**不单独写 Expected Output**
  - 因为 `AndCheckResp[<RespCode>]` 已内嵌检查

### 1.5.5 特殊规则

1. 这里遍历的是 **“除支持列表以外”的全部子功能**。
2. 若当前会话下服务有效，但遍历到的子功能全局不支持，预期 `0x12`。
3. 不要把本应在 Session Layer 中验证的“支持但当前会话不允许”的目标子功能混到 traversal 中。

---

## 1.6 S3 Server Timer Test

### 1.6.1 用例数量规则

**通用公式：**

- **物理寻址**：**1 条**（S3 未超时，会话保持）
- **功能寻址**：**2 条**（S3 未超时 + S3 超时返回 Default）

> **关键规则**：物理寻址和功能寻址的 S3 用例数量不同。
> - 物理寻址只需验证"S3 未超时会话保持"（1 条）
> - 功能寻址需同时验证"保持"和"超时返回 Default"（2 条）
> - 如果项目有特殊要求，按客户规则覆盖

### 1.6.2 用例命名规则

- `S3Server maintains the Session without timeout`
- `S3Server returns to the default Session upon timeout`

### 1.6.3 测试步骤模板

#### A. 未超时
1. 进入 Default
2. 进入 Extended（或其它非默认会话）
3. `Delay[<S3 - delta>]ms;`
4. `Send DiagBy[Physical]Data[22 F1 86];`

#### B. 已超时
1. 进入 Default
2. 进入 Extended（或其它非默认会话）
3. `Delay[<S3 + delta>]ms;`
4. `Send DiagBy[Physical]Data[22 F1 86];`

其中：

- `<S3>` 来自 `S3Server`
- `delta` 建议至少 100ms，避免边界抖动

### 1.6.4 Check 规则

- 未超时：
  - 第 4 步：`Check DiagData[62 F1 86 03]Within[50]ms;`
- 已超时：
  - 第 4 步：`Check DiagData[62 F1 86 01]Within[50]ms;`

### 1.6.5 特殊规则

1. S3 必须用 **读会话 DID** 来验证最终会话状态；不要只看是否能继续发请求。
2. **物理寻址只生成 1 条**（S3 未超时会话保持），不生成超时用例。
3. **功能寻址生成 2 条**（S3 未超时 + S3 超时返回 Default）。
4. 功能寻址版中：
   - 会话切换用 `Function`
   - S3 超时后的状态确认仍推荐用 `Physical + 22 F1 86`

---

## 1.7 Incorrect Diagnostic Command Test


### 1.7.1 用例数量规则

**通用公式：**

- **固定 2 条 / 每种支持的寻址方式**

两类错误：

1. SF_DL > 合法长度（如 `SF_DL=3`，合法为 2）
2. SF_DL < 合法长度（如 `SF_DL=1`，合法为 2）

> **注意**：客户当前参考模板中 **不包含 DLC 错误测试**（DLC < 8 / DLC > 8），只测 SF_DL 异常。
> 若项目后续明确要求增加 DLC 错误帧测试，可扩展为 4 条。

### 1.7.2 用例命名规则

沿用 PDF 原文：

- `When a diagnostic message with DLC < 8 is sent, ECU does not respond`
- `When a diagnostic message with DLC > 8 is sent, ECU responds normally`
- `Valid SF_DL=2, invalid SF_DL > 2...`
- `Valid SF_DL=2, invalid SF_DL < 2...`

### 1.7.3 测试步骤模板

#### A. SF_DL > 2
`Send DiagBy[<Addr>]Data[10 01]WithLen[3];`

#### B. SF_DL < 2
`Send DiagBy[<Addr>]Data[10 01]WithLen[1];`

### 1.7.4 Check 规则

- SF_DL > 2：
  - `Check DiagData[7F 10 13]Within[50]ms;`
- SF_DL < 2：
  - `Check DiagData[7F 10 13]Within[50]ms;`

### 1.7.5 特殊规则

1. 0x10 的合法 SF_DL 为 **2 字节数据负载**（SID + Subfunction）。
2. SF_DL 错误测试使用 `Send DiagBy...WithLen[...]`。
3. 测试前需先进入 Default Session 建立诊断会话。

---

## 1.8 NRC Priority Test


### 1.8.1 用例数量规则

- **固定 1 条 / 每个软件域 / 物理寻址**

> NRC Priority Test 只用于物理寻址。功能寻址不重复生成。

### 1.8.2 用例命名规则

`NRC <NRC_Priority_Chain>`

例如：`NRC 13>12>22`

其中 `<NRC_Priority_Chain>` 来自输入表的 `Negative response codes` 字段，按优先级排列。

### 1.8.3 测试步骤模板

**目标**：验证当多个 NRC 条件同时满足时，ECU 返回优先级最高的 NRC。

1. 进入 Default Session
2. 构造一个同时触发多个 NRC 条件的请求

**构造方法**（按 NRC 优先级从高到低）：

- `NRC 0x13`：发送超长/超短数据（如 `10 01 00`，长度异常触发 0x13）
- `NRC 0x12`：发送不支持的子功能（如 `10 FE`）
- `NRC 0x22`：在不满足前置条件的会话下请求

**通用步骤**：
1. `Send DiagBy[Physical]Data[10 <Sub> <ExtraBytes>];`

其中 `<Sub>` 选取一个当前会话下不支持的子功能，同时 `<ExtraBytes>` 使长度异常。

### 1.8.4 Check 规则

- 验证返回的 NRC 是优先级最高的那个
- 例如 NRC 链 `13>12>22`：同时触发 0x13 和 0x12 条件时，ECU 应返回 `7F 10 13`

### 1.8.5 特殊规则

1. NRC 优先级顺序来自输入表的 `Negative response codes` 字段（如 `13>12>22`）。
2. 该测试验证的是 ECU 的 NRC 仲裁逻辑，不是单一条件。
3. 如果输入表未给出 NRC 优先级链，则跳过本类测试。
4. 测试步骤只需 1 条，但必须同时触发至少 2 个 NRC 条件。

---

> **注意**：0x11 (ECUReset) 的规则已迁移至独立文件 `prompts/service_0x11_prompt.md`。
> 本文件仅包含 0x10 (DiagnosticSessionControl) 的规则。
