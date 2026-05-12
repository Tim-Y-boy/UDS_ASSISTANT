# Service 0x2E WriteDataByIdentifier — 用例生成规则

## 服务概述

- **Service ID**: 0x2E
- **Service Name**: WriteDataByIdentifier
- **正响应 SID**: 0x6E（0x2E + 0x40）
- **负响应格式**: `7F 2E <NRC>`
- **请求格式**: `2E <DID_H> <DID_L> <WriteData...>`
- **无 Subfunction**（DID 替代子功能角色）
- **合法 SF_DL**: 3 + ByteLength（SID + DID + 数据）
- **关键特性**: 不存在 NRC 0x12；写入数据需用 DefaultValue 填充；0x20 填充未使用字节

### 正响应格式

- `6E <DID_H> <DID_L>`（仅确认，不回显数据）

### 典型 NRC

| NRC  | 含义 | 触发条件 |
|------|------|---------|
| 0x13 | Incorrect Message Length Or Invalid Format | 报文长度错误 |
| 0x22 | Conditions Not Correct | 写入条件不满足 |
| 0x31 | Request Out Of Range | DID 不支持写入 |
| 0x33 | Security Access Denied | 需要安全解锁但未解锁 |
| 0x72 | General Programming Failure | 写入失败（如存储器错误） |
| 0x7F | Service Not Supported In Active Session | 当前会话下不支持 0x2E 服务 |

---

## 生成分类（共 4 类）

按以下固定顺序逐类生成，每个分类使用 `## N.N` 作为标题（如 `## 1.1 Session Layer Test`）。

---

### 分类 1: Session Layer Test

#### 用例数量规则

- `Npos` = 可写 DID × 支持的会话数（Write Support = Y 的 DID）
- `Nneg_did` = 不可写 DID case 数（Write Support = N）
- `Nneg_sess` = 不支持的会话 case 数
- **总数 = Npos + Nneg_did + Nneg_sess**

#### 用例命名规则

- 正向：`<CurrentSessionName> Session support the 0x2E service write DID 0x<DID>`
  - 示例：`Extended Session support the 0x2E service write DID 0xF101`
- 负向（DID 不可写）：`DID 0x<DID> does not support write operation`
- 负向（会话不支持）：`<CurrentSessionName> Session nonsupport 0x2E service write DID 0x<DID>`

#### 测试步骤模板

**A. 不支持的会话（如 Default）**
```
1. 进入 Default 会话
2. Send DiagBy[Physical]Data[2E <DID_H> <DID_L> <WriteData>];
```

**B. 支持会话但未解锁（Access Level 限制）**
```
1. 进入支持的会话（Extended）
2. Send DiagBy[Physical]Data[2E <DID_H> <DID_L> <WriteData>];
```

**C. 不可写的 DID（Write Support = N）**
```
1. 进入支持的会话
2. Send DiagBy[Physical]Data[2E <DID_H> <DID_L> <WriteData>];
```

#### Check 规则

**A. 不支持的会话：**
- `Check DiagData[7F 2E 7F]Within[50]ms;`

**B. 支持会话但未解锁：**
- `Check DiagData[7F 2E 33]Within[50]ms;`（Security Access Denied）

**C. 不可写的 DID：**
- `Check DiagData[7F 2E 31]Within[50]ms;`（Request Out Of Range）

#### 数据填充规则

| 场景 | 填充方式 |
|------|---------|
| DID 有 DefaultValue | 使用 DefaultValue（如 0x11 重复 ByteLength 次） |
| DID 有未使用位 | 使用 0x20（空格）填充 |
| 示例 DID 0xF101 | 17 字节，写入数据 = `11 11 11 11 11 11 11 11 11 11 11 11 11 11 11 11 11` |

---

### 分类 2: Secure Access Test

#### 用例数量规则

- 仅对 Write Access Level 包含安全限制的 DID 生成
- **总数 = N_did_write_need_security**

#### 用例命名规则

`Security access Lx unlock supports 0x2E service write DID 0x<DID>`
- 示例：`Security access L2 unlock supports 0x2E service write DID 0xF101`

#### 测试步骤模板

```
1. 进入支持的会话（通常 Extended）
2. Send DiagBy[Physical]Data[27 <SeedSub>]AndCheckResp[PostiveResponse];
3. Send Security Right KeyBy[Physical]Level[<KeySub>];
4. Send DiagBy[Physical]Data[2E <DID_H> <DID_L> <WriteData>];
5. Send DiagBy[Physical]Data[22 <DID_H> <DID_L>];
```

#### Check 规则

- 第 3 步：`Check DiagData[67 <KeySub>]Within[50]ms;`
- 第 4 步：`Check DiagData[6E <DID_H> <DID_L>]Within[50]ms;`
- 第 5 步：`Check DiagData[62 <DID_H> <DID_L> <WrittenData>]Within[50]ms;`（读回验证数据一致）

#### 特殊规则

1. 安全等级从 DID 表的 Write Access Level 字段读取
2. 写入后应使用 0x22 读回验证数据一致性
3. 仅对 Write Support = Y 的 DID 生成

---

### 分类 3: DID Storage Test（写入持久化验证）

#### 用例数量规则

- 仅对 Storage = EEPROM/FLASH（非易失性存储）的 DID 生成
- **总数 = N_did_nonvolatile**

#### 用例命名规则

`DID 0x<DID> write data persistence after power reset`
- 示例：`DID 0xF101 write data persistence after power reset`

#### 测试步骤模板

```
1. 进入支持的会话（Extended）
2. 完成安全解锁
3. Send DiagBy[Physical]Data[2E <DID_H> <DID_L> <TestData>];
4. Send DiagBy[Physical]Data[22 <DID_H> <DID_L>];
5. Set Voltage[0]V;
6. Delay[1000]ms;
7. Set Voltage[12]V;
8. Delay[1000]ms;
9. Send DiagBy[Physical]Data[10 03];
10. Send DiagBy[Physical]Data[22 <DID_H> <DID_L>];
```

#### Check 规则

- 第 3 步：`Check DiagData[6E <DID_H> <DID_L>]Within[50]ms;`
- 第 4 步：`Check DiagData[62 <DID_H> <DID_L> <TestData>]Within[50]ms;`（写入后读回一致）
- 第 10 步：`Check DiagData[62 <DID_H> <DID_L> <TestData>]Within[50]ms;`（断电后仍一致）

#### 特殊规则

1. 仅对非易失性存储（EEPROM/FLASH）的 DID 才需要此测试
2. RAM 存储的 DID 断电后数据丢失，不做持久化验证
3. 测试完成后必须写回原始值（恢复出厂值）
4. 步骤 5-8 为电源复位，步骤 9 重新进入会话

---
### 分类 4: NRC Test（故障码测试）
#### 用例数量规则

#### 测试步骤模板

```
1. 进入不支持的会话（Default）
2. Send DiagBy[Physical]Data[2E <DID_H>];
```

#### Check 规则

- 第 1 步：`Check DiagData[7F <Service ID> <NRC code>]Within[50]ms;`（回复NRC故障码）

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

当 `Functional Request = 不支持` 时（0x2E 典型情况）：
- 仅生成 1 条 No_Response 验证用例

---

## DID 写入数据填充规则

| 场景 | 填充方式 |
|------|---------|
| DID 有 DefaultValue | 使用 DefaultValue |
| DID 未使用位 | 使用 0x20（空格 ASCII）填充 |
| 字符串型 DID | 使用 0x11 或实际字符串 |
| 数值型 DID | 使用实际值或 xx |

---

## 生成注意事项

1. **Case ID 不可重复**，物理寻址 `Diag_0x2E_Phy_001` 起递增
2. **每个 Send 都要有对应 Check**
3. **写入后必须用 0x22 读回验证**，确认数据一致性
4. **DID 列表从 DID 表读取**，Write Support = Y 的才生成正向 case
5. **0x2E 无子功能概念**，不存在 NRC 0x12，不可写的 DID 返回 NRC 0x31
6. **未解锁写入返回 NRC 0x33**（Security Access Denied）
7. **持久化测试后必须恢复原始值**
8. **输出格式严格为 pipe table**，列顺序：`| Case ID | Case名称 | 测试步骤 | 预期输出 |`
9. **顶级标题使用 `#`**：如 `# 1. Application Service_Physical Addressing`、`# 2. Application Service_Functional Addressing` 等
10. **分类标题使用 `##`**：如 `## 1.1 Session Layer Test` 等
11. **各大组之间用 `---` 分隔**
12. **无符合条件的用例时使用 `>` 引用**
13. **步骤中换行使用 `<br>` 标记**，不用 `\n`
