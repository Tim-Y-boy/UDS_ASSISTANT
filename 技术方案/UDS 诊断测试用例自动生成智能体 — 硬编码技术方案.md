## 1. 项目概述

### 1.1 背景

汽车电子 ECU 的 UDS（Unified Diagnostic Services）测试用例编写面临以下痛点：

- **规则复杂**：涉及 ISO 14229-1:2020、ISO 15765-2:2016 标准协议，叠加客户企业定制规则，单服务可能包含 7 大类、数十条用例
- **人工耗时**：11 个服务的人工编写通常需要数周，且高度依赖工程师经验
- **易出错**：正/负响应格式、NRC 编码、SPRMIB 抑制位、会话切换路径等细节容易遗漏
- **难以规模化**：不同 ECU 项目参数不同，每次需重新编写

### 1.2 目标

构建一个完整的 Web 应用系统，实现：

- 输入：用户上传的 ECU 诊断参数 Excel 文件（**格式不固定**）
- 输出：符合 ISO 14229 和企业标准的完整测试用例
- 覆盖全部 11 个 UDS 服务（0x10/0x11/0x14/0x19/0x22/0x27/0x28/0x2E/0x31/0x3E/0x85）
- 规则准确率 ≥ 95%
- 提供 Web 界面，支持在线生成、预览、导出

### 1.3 智能体描述

将汽车电子 UDS 诊断测试业务与人工智能技术相结合，通过构建规则引擎与智能体协同系统，实现 ECU 诊断参数表的智能解析、ISO 14229 协议规则的自动匹配、多服务多分类测试用例的批量生成与 NRC/SPRMIB/会话矩阵的精准覆盖，从而将资深 UDS 测试工程师的隐性经验显性化、规则化、系统化，最终实现将 UDS 诊断测试用例设计工作从人工逐条编写转变为"输入参数表即可一键输出全量标准化用例"，单服务用例编写效率从数天缩短至分钟级，规则准确率达到 95% 以上，彻底消除不同工程师编写风格和覆盖粒度的人为差异。

### 1.4 边界与约束

| 范围                    | 说明                                                |
| --------------------- | ------------------------------------------------- |
| **不做**模型微调            | 纯提示词工程                                            |
| **不用** RAG            | 输入是结构化 Excel，直接 LLM 解析，不需要向量检索                    |
| **不用** LangChain/Dify | 固定管道任务，裸 SDK 更可控                                  |
| **不固定**输入 Excel 格式    | Service ID、Subfunction 等核心语义字段不变，但列顺序/Sheet名/排版可变 |
| **提供** Web 前后端        | FastAPI 后端 + 低代码前端，嵌入部署到泰能                        |

---

## 2. 系统架构

### 2.1 整体架构

```
┌──────────────────────────────────────────────────────────────────────┐
│                         前端（嵌入式 SPA）                            │
│                                                                     │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ 门户首页 │  │ 用例生成  │  │ 历史记录  │   │ 预览导出  │              │
│  │ (Portal)│  │(Generate)│  │(History) │  │(Preview) │              │
│  └────┬────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘              │
│       │            │              │              │                  │
│       └────────────┴──────────────┴──────────────┘                  │
│                           │ HTTP / SSE                              │
├───────────────────────────┼─────────────────────────────────────────┤
│                           ▼                                         │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              FastAPI 后端（api.py）                          │    │
│  │                                                             │    │
│  │  POST /api/generate        批量同步生成                       │    │
│  │  POST /api/generate/stream SSE 流式生成                      │    │
│  │  POST /api/export          导出 Excel                       │    │
│  │  POST /api/export/json     导出 JSON                        │    │
│  │  GET  /api/services        获取服务列表                      │    │
│  │  GET  /health              健康检查                          │    │
│  └────────────────────────┬────────────────────────────────────┘    │
│                           │                                         │
│                           ▼                                         │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              智能体处理管道（Python 核心引擎）                  │    │
│  │                                                             │    │
│  │  ┌───────────────┐    ┌───────────────┐    ┌────────────┐   │    │
│  │  │ Excel 读取框架 │───▶│ 参数提取管道    │───▶│ 混合生成    │  │    │
│  │  │(excel_framework)│  │ (pipeline)    │    │(generate_  │  │    │
│  │  │               │    │               │    │ pipeline)  │  │    │
│  │  └───────────────┘    └───────┬───────┘    └─────┬──────┘  │    │
│  │                               │                   │        │    │
│  │                    ┌──────────┴──────────┐        │        │    │
│  │                    │   LLM 网关客户端     │◀───────┘        │    │
│  │                    │  (llm_client)       │  多提供商故障转移 │    │
│  │                    │  OpenRouter/Kimi    │                 │    │
│  │                    │  /DeepSeek/vLLM    │                  │    │
│  │                    └────────────────────┘                  │    │
│  │                                                            │    │
│  │  ┌───────────────┐  ┌──────────────┐  ┌────────────────┐   │    │
│  │  │ JSON 响应解析  │  │ Excel 导出    │  │Pydantic Schema │   │    │
│  │  │(response_parser)││(excel_export)│  │  (schemas)     │   │    │
│  │  └───────────────┘  └──────────────┘  └────────────────┘   │    │
│  │                                                            │    │
│  │  ┌──────────────────────────────────────────────────────┐   │    │
│  │  │  模板生成器 (template_generator)                      │   │    │
│  │  │  Incorrect Command / NRC Priority / Session Layer    │   │    │
│  │  │  SPRMIB / Secure Access / Sub-function Traversal    │   │    │
│  │  │  DID Range — 约 40% 用例由确定性代码生成               │   │    │
│  │  └──────────────────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    提示词资产层（prompts/）                    │    │
│  │  base_prompt + 11个 service_prompt + extract_prompt          │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 混合生成架构（硬编码模板 + LLM）

经 Dify 输出与 Excel 标准对比分析发现，约 40% 的测试用例属于参数排列组合（Session Layer、SPRMIB、Incorrect Command、NRC Priority、Sub-function Traversal），可由确定性代码 100% 准确生成，无需 LLM 参与。系统采用混合生成架构：

```
FullExtractionResult ─┬→ template_generator (40% 硬编码, 100% 准确)
                      │   Incorrect Command / NRC Priority / Session Layer
                      │   SPRMIB / Secure Access / Sub-function Traversal
                      │   DID Range / Functional Nonsupport
                      │
                      └→ LLM (仅 60% 复杂类别) → 解析 → 合并 → 重编号
                          ECU Reset / S3 Timer / Clear DTC / DTC Function
                          DID Read/Write / Security Mechanism / ...
```

**优势**：
- 硬编码部分零幻觉，正响应 hex/NRC 码/会话路径 100% 正确
- LLM 仅处理需要语义推理的复杂类别，token 消耗减少 40-60%
- 输出格式由模板保证，不再依赖 LLM 的格式遵从度

**两次 LLM 调用分工**：

|                 | 第 1 次调用（参数提取）          | 第 2 次调用（用例生成，仅 LLM 类别） |
| --------------- | ---------------------- | --------------------------- |
| **输入**          | Excel 原始文本（openpyxl 读取） | Service Prompt + 参数 + 类别限制指令 |
| **任务**          | 结构化数据抽取 → JSON         | 仅生成 LLM 负责的类别用例          |
| **temperature** | 0.05（极低，保证确定性）         | 0.05（极低，保证确定性）              |
| **max_tokens**  | ~8,000                 | ~8,000 ~ 16,000（减少）        |
| **耗时预估**        | 2-5 秒                  | 5-30 秒（用例数减少）               |

### 2.3 为什么不用 RAG

| RAG 适用场景 | 本项目实际场景 |
| --- | --- |
| 海量非结构化文档 | 1 个结构化 Excel 文件 |
| 需要语义相似度检索 | 解析目标是确定的字段 |
| 检索结果不确定 | LLM 直接从文本提取 JSON |
| 需要 Embedding + 向量库 | openpyxl 读文本 + LLM 提取即可 |
| 知识频繁更新 | 协议知识静态，已预编译进提示词 |

**补充说明**：本项目的领域知识（ISO 14229 协议规则、NRC 码表、CAPL 函数 API、编写规范）全部已从参考文档中提取并"烘焙"进提示词模板。运行时无需检索任何外部文档，提示词本身就是知识的编译产物。

---

## 3. 技术选型

| 组件           | 选型                      | 理由                                |
| ------------ | ----------------------- | --------------------------------- |
| **后端框架**     | FastAPI                 | 异步支持、自动 OpenAPI 文档、SSE 原生支持       |
| **前端**       | JAVA+Vue                | 嵌入式部署到公司泰能平台                      |
| **Excel 读取** | openpyxl + MCP Server   | 轻量、纯 Python、支持 xlsx，MCP 提供标准化解析接口 |
| **参数提取**     | LLM（多模型故障转移）            | 格式不固定，LLM 语义理解替代关键词匹配             |
| **提示词模板**    | Markdown 文件 + Python 组装 | 简单直接，易于版本管理和迭代                    |
| **LLM 调用**   | httpx + OpenAI 兼容协议     | 多提供商自动故障转移，无需额外框架                 |
| **数据校验**     | Pydantic v2             | 类型安全、自动校验、默认值填充                   |
| **输出校验**     | Python 正则 + 规则检查        | NRC 格式、步骤配对、ID 唯一性                |
| **流式输出**     | SSE（Server-Sent Events） | 实时推送生成进度，无需 WebSocket             |
| **语言**       | Python 3.10+            | 全管道在 Python，无跨语言开销                |

---

## 4. 知识架构与资产溯源

### 4.1 知识"预编译"策略

本项目的核心设计决策是：**将所有领域知识提前提取并结构化地写入提示词模板，而非运行时动态检索**。这类似于编译型语言与解释型语言的区别——提示词是"编译"后的知识产物，运行时只需执行，无需再"解释"源文档。

```
┌─────────────────────────────┐      提取 & 结构化      ┌──────────────────────────┐
│     知识源文档（开发时）       │  ──────────────────→   │    提示词资产（运行时）     │
│                             │                        │                         │
│ 和而泰Ai需求.pdf (45页)       │                        │ Base Prompt (~3,100 tok)│
│ auto_test.md                │                        │ Service Prompt ×11      │
│ 汽车电子函数接口定义.docx      │                        │ Extract Prompt          │
│ NRC_list.xlsx (11条)        │                        │                         │
│ UDS诊断调查表字段解析规则.docx │                        │                         │
│ UDS测试用例大纲.html         │                        │                          │
│ 478条人工用例(逆向推导)       │                        │                          │
└─────────────────────────────┘                        └──────────────────────────┘
```

### 4.2 运行时 vs 开发时的文件依赖

| 场景 | 需要的文件 | 说明 |
| --- | --- | --- |
| **运行时（生产环境）** | prompts/*.md + config.yaml + 用户 Excel | 提示词自包含，无需外部文档 |
| **开发/维护** | support_data/* 全部 | 规则变更时需回溯到源文档更新提示词 |
| **验证/回归测试** | input/* + output/* + support_data/* | 用作准确性比对的黄金标准 |

---

## 5. 前端设计

### 5.1 页面结构

基于原型设计，前端包含以下核心页面：
![[1776922517989_719fdc5081294f10ba020ae47fd3241d.png]]
![[1776922502649_84e41e369b1b4080a708f59ddb23f9df.png]]
![[1776922488821_430eadeed9f640fe84a78e1f9b392925.png]]
![[1776922474044_a7027af3fd0041c8ae4cf34677967e14.png]]
![[1776922457161_36a19fcb291242fc8a4c18c7e3c908ba.png]]


### 5.2 页面详细设计

#### 5.2.1 用例生成页面

左侧边栏导航包含"用例生成"和"历史记录"两个入口。主内容区采用两步向导：

**Step 1 — 上传需求文档**
- 支持拖拽上传 `.xls`/`.xlsx` 文件
- 上传后显示文件名、大小，支持删除重传
- 文件格式前端校验（扩展名 + 大小限制）

**Step 2 — 生成测试用例**
- 服务选择：11 个 UDS 服务以复选框网格展示，支持全选/反选
- 点击"生成用例"后通过 SSE 实时展示每个服务的生成进度
- 生成完成后自动跳转到结果预览

**SSE 流式进度**：
```
event: progress
data: {"service_id": "0x10", "status": "extracting", "message": "提取参数中..."}

event: progress
data: {"service_id": "0x10", "status": "generating", "message": "LLM 生成用例中..."}

event: complete
data: {"service_id": "0x10", "case_count": 52, "elapsed_seconds": 25.3}
```

#### 5.2.2 结果预览页面

- Tab 切换不同服务的测试用例
- 每个服务展示：用例列表、分类统计、token 用量、耗时
- JSON 查看器：查看结构化提取参数
- 操作栏：导出 Excel / 导出 JSON

#### 5.2.3 历史记录页面

- 列表展示历史生成记录
- 支持按日期、服务 ID 筛选
- 支持重新加载历史结果

---

## 6. 后端设计

### 6.1 架构模式

```
FastAPI 应用
├── 嵌入式前端（GET / 返回 SPA HTML）
├── API 路由层（/api/*）
│   ├── /api/generate          → 批量同步生成
│   ├── /api/generate/stream   → SSE 流式生成
│   ├── /api/export            → 导出 Excel
│   ├── /api/export/json       → 导出 JSON
│   ├── /api/services          → 获取服务列表
│   └── /health                → 健康检查
├── 业务逻辑层
│   ├── UDSExtractionPipeline  → 参数提取管道
│   ├── UDSGeneratePipeline    → 用例生成管道
│   └── ExcelExportService     → Excel 导出服务
├── 基础设施层
│   ├── LLMClient              → 多提供商 LLM 网关
│   ├── ExcelReader            → Excel 读取框架
│   └── SheetTextConverter     → 文本转换器
└── 数据模型层
    ├── schemas.py             → 提取结果 Pydantic 模型
    └── test_schemas.py        → 测试用例 Pydantic 模型
```

### 6.2 API 接口规范

#### 6.2.1 SSE 流式生成（核心接口）

```
POST /api/generate/stream
Content-Type: application/json

Request:
{
    "excel_path": "uploads/xxx.xlsx",
    "service_ids": ["0x10", "0x22", "0x27"]
}

Response: text/event-stream
event: progress
data: {"service_id": "0x10", "status": "extracting", "progress": 0.3}

event: complete
data: {"service_id": "0x10", "case_count": 52, "test_cases": [...], "meta": {...}}

event: error
data: {"service_id": "0x10", "error": "ERR_LLM_UNAVAILABLE: ..."}

event: done
data: {"total_cases": 156, "elapsed_seconds": 45.2}
```

#### 6.2.2 导出接口

```
POST /api/export
Content-Type: application/json

Request:
{
    "results": [...],       // 生成结果
    "format": "xlsx"        // "xlsx" | "json"
}

Response: application/octet-stream (Excel 文件下载)
```

### 6.3 多用户并发架构（10~50 人）

#### 6.3.1 并发瓶颈分析

| 瓶颈 | 原因 | 影响 |
| --- | --- | --- |
| LLM 调用耗时长 | 单服务生成 10~60s，11 个服务串行约 3~10 分钟 | 多用户请求排队 |
| 无状态持久化 | 结果只存在内存中 | 断线丢失、无法查看历史 |
| 单进程限制 | Uvicorn 单 worker 无法利用多核 | CPU 密集解析（openpyxl）阻塞事件循环 |

#### 6.3.2 架构方案

采用 **Redis 任务队列 + Celery Worker** 模式：

```
用户 A ──┐                    ┌── Celery Worker 1 ──→ LLM API
用户 B ──┤                    ├── Celery Worker 2 ──→ LLM API
用户 C ──┼──▶ FastAPI ──▶ Redis ◄── Celery Worker 3 ──→ LLM API
  ...    │     (4 workers)   ││
用户 N ──┘                    │└── Celery Worker N
                              │
                         Redis 存储
                         ├─ 任务队列 (FIFO)
                         ├─ 任务状态 (task_id → status/result)
                         └─ 用户会话 (task_id → user_id)
```

**请求生命周期**：

```
1. 用户提交 → FastAPI 生成 task_id → 任务入 Redis 队列 → 返回 task_id
2. Celery Worker 取任务 → 执行提取+生成 → 每完成一个服务，更新 Redis 中的进度
3. 前端通过 SSE 轮询 /api/task/{task_id}/events 获取实时进度
4. 全部完成 → 结果存入 Redis → 前端展示 → 支持导出
```

#### 6.3.3 关键技术选型

| 组件 | 选型 | 说明 |
| --- | --- | --- |
| 任务队列 | Celery + Redis | 成熟的 Python 异步任务方案，支持任务优先级、重试、超时 |
| 结果存储 | Redis（短期）+ SQLite/PostgreSQL（长期） | Redis 存热数据，数据库存历史记录 |
| 进度推送 | SSE 轮询 Redis | Worker 写进度到 Redis，FastAPI 异步轮询并推送 |
| 进程管理 | Supervisor / systemd | 管理 Celery Worker 和 FastAPI 进程 |

#### 6.3.4 核心代码改动

```python
# tasks.py — Celery 任务定义
from celery import Celery

app = Celery('uds', broker='redis://localhost:6379/0')

@app.task(bind=True)
def generate_task(self, task_id: str, excel_path: str, service_ids: list):
    for sid in service_ids:
        # 更新进度到 Redis
        redis.set(f"task:{task_id}", json.dumps({
            "status": "generating",
            "current": sid,
            "completed": completed,
            "total": len(service_ids)
        }))
        # 执行生成
        result = generate_pipeline.generate(excel_path, sid)
        # 存储单个服务结果
        redis.set(f"task:{task_id}:{sid}", result.json())
    # 标记完成
    redis.set(f"task:{task_id}", json.dumps({"status": "done", ...}))
```

```python
# api.py — SSE 进度查询端点
@app.get("/api/task/{task_id}/events")
async def task_events(task_id: str):
    async def stream():
        while True:
            data = redis.get(f"task:{task_id}")
            yield f"data: {data}\n\n"
            if json.loads(data).get("status") in ("done", "failed"):
                break
            await asyncio.sleep(1)
    return EventSourceResponse(stream())
```

#### 6.3.5 并发容量估算

| 配置 | Worker 数 | 并发用户数 | 说明 |
| --- | --- | --- | --- |
| 最低配置 | 2 Worker | ~10 人 | 每人排队约 5 分钟 |
| 推荐配置 | 4 Worker | ~30 人 | 大部分请求 1 分钟内开始处理 |
| 高配 | 8 Worker | ~50 人 | 需确认 LLM API 并发限额 |

**LLM 瓶颈**：真正的瓶颈不在 Python 侧，而在 LLM API 的并发限额。当前使用云端 API（OpenRouter/Kimi），单 key 并发约 5~10 请求。多 Worker 场景下需确认 API 套餐的 RPM 限制，必要时升级套餐或部署本地 vLLM。

---

## 7. 模块详细设计

### 7.1 模块一：Excel 文本转换器（excel_framework）

**职责**：用 openpyxl 将 Excel 每个 Sheet 转为 LLM 可读的纯文本。

**核心组件**：

| 文件 | 职责 | 代码行数 |
| --- | --- | --- |
| `reader.py` | Excel 文件读取、Sheet 遍历、合并单元格处理 | ~164 行 |
| `text_converter.py` | 文本格式化、智能 Sheet 过滤、相关度匹配 | ~110 行 |
| `value_normalizer.py` | 值归一化（Y/N → bool、hex 标准化） | ~69 行 |

**智能 Sheet 过滤**：基于配置的关键词匹配，自动过滤无关 Sheet（如历史记录、修订日志、模板说明），只保留包含诊断参数的相关 Sheet。

**处理细节**：
- `data_only=True` 读取公式计算结果
- 合并单元格：openpyxl 自动处理，左上角有值，其余为 None
- 最大行数限制：200 行（可配置）
- 空值跳过，保持文本紧凑

### 7.2 模块二：LLM 参数提取器（pipeline）

**职责**：用 LLM 从 Excel 文本中提取结构化 JSON 参数，同时提取 App 和 Boot 双域数据。

**输入**：Excel 文本 + 目标 Service ID

**输出**：`FullExtractionResult`（Pydantic 模型）

**提取的数据结构**：

```python
class FullExtractionResult(BaseModel):
    basic_info: BasicInfo           # ECU基本参数（含P2/P2* hex编码、NRC优先级链）
    service_matrix: ServiceMatrix   # App域服务子功能矩阵
    boot_matrix: ServiceMatrix      # Boot域服务子功能矩阵（可选）
    did_list: list[DIDEntry]        # DID列表（0x22/0x2E用）
    dtc_list: list[DTCEntry]        # DTC列表（0x14/0x19用，含触发/恢复方法）
    routine_list: list[RIDEntry]    # RID列表（0x31用）
    security_list: list[SecurityAccessEntry]   # 安全访问映射（Seed/Key子功能对）
    reset_subfunctions: list[ResetSubfunctionEntry]  # ECU Reset子功能列表
    k_column_rules: list[str]       # 业务规则
```

**提取策略**：
- P2/P2* 时间参数同时提供 ms 值和预计算的 hex 编码值
- NRC 优先级链保持 `>` 分隔符顺序（如 `13>12>22>7E`）
- 安全访问映射提取 Seed/Key 子功能对（如 L2→27 03/04）
- App/Boot 双域子功能矩阵同时提取，标注域标签
- 子功能表包含完整的会话支持、寻址支持、访问等级信息
- DTC 列表新增触发/恢复方法字段（`trigger_method`、`trigger_delay_ms`、`recovery_method`、`recovery_delay_ms`），用于 Clear DTC、Read DTC 等服务测试中的故障制造步骤

### 7.3 模块三：提示词组装器（prompt_loader）

**职责**：将提取的结构化参数格式化为 LLM 可读的 user message，注入动态 hex 值。

**关键设计**：

1. **动态 hex 值**：P2/P2* 的 hex 编码值从提取结果动态获取，不再硬编码
2. **双域参数注入**：App 域和 Boot 域的子功能矩阵分别以 Markdown 表格注入
3. **辅助数据注入**：安全访问映射、0x11 子功能列表、DID/DTC/RID 列表按需注入
4. **输出格式模板**：正响应报文示例中的 hex 值全部动态计算（如 `50 01 00 32 00 C8`）
5. **混合生成支持**：`build_generation_user_message()` 新增 `llm_categories`、`next_phy_id`、`next_fun_id` 参数
   - 当 `llm_categories` 非空时，生成指令仅请求 LLM 负责的类别，避免与模板生成器重复
   - Case ID 起始编号根据模板生成器已生成的数量动态偏移

### 7.4 模块四：模板生成器（template_generator）

**职责**：用硬编码模板确定性生成约 40% 的测试用例，消除 LLM 幻觉，确保参数级别 100% 准确。

**核心思路**：部分测试用例类别本质是参数的排列组合（如会话层遍历、SPRMIB 测试），其生成逻辑是确定性的，无需 LLM 参与。将这些类别从 LLM 卸载到代码后，既消除幻觉又减少 token 消耗。

**代码规模**：~900 行（`src/uds_agent/template_generator.py`）

**类别注册表**：

```python
# 每个 service 的硬编码类别列表
HARDCODED_CATEGORIES: dict[str, list[str]] = {
    "0x10": ["incorrect_command", "nrc_priority", "subfunction_traversal",
             "sprmib", "session_layer", "secure_access"],
    "0x11": ["incorrect_command", "subfunction_traversal",
             "sprmib", "session_layer", "secure_access"],
    # ... 所有 11 个服务
}

# 每个 service 的 LLM 负责类别列表
LLM_CATEGORIES: dict[str, list[str]] = {
    "0x10": ["ecu_reset", "s3_timer"],
    "0x14": ["clear_dtc_function"],
    "0x27": ["security_mechanism"],
    # ...
}
```

**服务配置表**：

```python
SERVICE_CONFIG: dict[str, dict] = {
    "0x10": {"sf_dl_legal": 2, "resp_prefix": "50", "has_subfunction": True},
    "0x11": {"sf_dl_legal": 2, "resp_prefix": "51", "has_subfunction": True},
    # ... 每个服务的协议参数
}
```

**生成器分层**：

| 层级 | 生成器 | 用例数 | 说明 |
| --- | --- | --- | --- |
| Tier 1 | `_gen_incorrect_command` | 4 条 | DLC<8/DLC>8/SF_DL>legal/SF_DL<legal |
| Tier 1 | `_gen_nrc_priority` | 1 条 | 触发最高优先级 NRC |
| Tier 1 | `_gen_subfunction_traversal` | 1-3 条 | 遍历不支持的子功能 |
| Tier 1 | `_gen_did_range` | 1 条 | 仅 0x22：DID 范围检查 |
| Tier 2 | `_gen_session_layer` | sessions×subfunctions | 会话层排列组合（最大量类别） |
| Tier 2 | `_gen_sprmib` | sessions×subfunctions | SPRMIB = 0x80 + Sub 模板 |
| Tier 2 | `_gen_secure_access` | security_levels×sessions | 安全解锁序列模板 |
| 特殊 | `_gen_functional_nonsupport` | 0-1 条 | 无功能寻址支持时的 No_Response |

**辅助函数**：

| 函数 | 职责 |
| --- | --- |
| `_session_enter_steps()` | 返回进入指定会话的 (steps, expected) 序列 |
| `_security_unlock_steps()` | 返回安全解锁的 Seed/Key 序列 |
| `_build_request_payload()` | 构建请求报文 hex 字符串 |
| `_build_positive_response()` | 构建正响应报文 hex 字符串 |
| `_p2_hex_display()` / `_p2star_hex_display()` | P2/P2* ms→hex 转换（用于测试步骤显示） |

**主入口**：

```python
def generate_hardcoded_cases(
    extraction: FullExtractionResult,
    service_id: str,
) -> list[dict]:
    """遍历 App/Boot × Phy/Fun，调用各类别生成器，返回原始字典列表"""
```

输出为原始字典（兼容 test_parser 内部格式），包含字段：`case_name`、`test_procedure`、`expected_output`、`section_name`、`is_boot`、`domain`、`addressing`、`category`、`priority`。

### 7.5 模块五：LLM 网关客户端（llm_client）

**职责**：多提供商 LLM 调用，自动故障转移。

**架构**：

![[Pasted image 20260423143929.png]]

**特性**：

| 特性       | 说明                                       |
| -------- | ---------------------------------------- |
| **多提供商** | 支持 OpenRouter、DeepSeek、通义千问、本地 vLLM      |
| **健康检查** | 时间窗口内连续失败 N 次自动标记为不健康                    |
| **重试策略** | 同一提供商内最多重试 1 次，temperature 递增            |
| **故障转移** | HTTP 403/429/502/503/504 自动切换到下一个提供商     |
| **超时控制** | 连接超时 10s，读取超时可配置（默认 600s）                |
| **成本追踪** | 每个 provider 配置 `cost_per_million` 用于成本估算 |

### 7.6 模块六：输出解析与校验

**test_parser**（~425 行）负责解析 LLM 生成的测试用例文本：
- 识别 `### N.M` 分类标题和 `#### N.M.N` 用例标题
- 提取 Case ID、Steps、Expected Output 三个字段
- 解析末尾的统计汇总表

**response_parser** 负责从 LLM 响应中提取 JSON：
- 处理直接 JSON、Markdown 代码块包裹、前后有额外文字等变体
- Pydantic v2 校验 + 宽松模式（校验失败时用默认值填充）

### 7.7 模块七：提示词变更日志

在 prompts/ 下维护一个变更日志文件 CHANGELOG.md：
- `service_0x2E_prompt.md`：补充 WriteDID 回读验证规则
- `extract_prompt.md`：新增 P2/P2* hex 编码提取要求
- 原因：对比 Dify 输出发现 hex 值缺失

---

## 8. 数据流详解

### 8.1 完整调用流程

```
用户上传 Excel + 选择服务 ID 列表
        │
        ▼
[excel_framework] openpyxl 读取 Excel
        │  输出: {Sheet名: 文本内容}
        │  智能过滤无关Sheet
        ▼
[pipeline] LLM 第1次调用 — 参数提取
        │  输入: Excel文本 + extract_prompt + service_id
        │  输出: FullExtractionResult JSON
        │  包含: basic_info + App/Boot双域矩阵 + 安全映射 + DTC触发方法 + ...
        │  耗时: 2-5秒
        ▼
    Pydantic 校验
        │  检查必填字段、P2 hex编码、子功能列表
        ▼
[template_generator] 模板生成（新增）
        │  输入: FullExtractionResult + service_id
        │  输出: 硬编码测试用例（~40% 总量，100% 准确）
        │  类别: incorrect_command / session_layer / sprmib / secure_access / ...
        │  耗时: <100ms（纯计算，无 LLM 调用）
        ▼
[prompt_loader] 提示词组装
        │  Service Prompt + 动态参数注入
        │  仅请求 LLM 负责的类别（排除硬编码类别）
        │  Case ID 起始编号动态偏移
        ▼
[llm_client] LLM 第2次调用 — 用例生成（仅复杂类别）
        │  输入: 完整提示词（已缩减 ~40-60% token）
        │  输出: 测试用例 Markdown 文本
        │  耗时: 10-60秒
        ▼
[_merge_and_renumber] 合并 + 重编号（新增）
        │  按 domain×addressing 分桶: App_Phy / App_Fun / Boot_Phy / Boot_Fun
        │  硬编码按类别排序在前，LLM 追加在后
        │  统一重编号 Case ID: Diag_{sid}_{addr}_{NNN}
        ▼
SSE 推送结果 → 前端展示
        │
        ▼
[excel_export] 用户导出 Excel / JSON
```

### 8.2 异常处理

| 异常场景 | 处理方式 |
| --- | --- |
| Excel 文件无法打开 | 返回 `ERR_FILE_INVALID` |
| 未找到目标服务行 | 返回 `ERR_SERVICE_NOT_FOUND` |
| LLM JSON 解析失败 | 重试 1 次（temperature 提高 0.05）；仍失败则返回原始输出 + 错误 |
| LLM 输出不完整 | 校验器标记 warnings，由用户决定是否接受 |
| 所有 LLM 提供商不可用 | 返回 `ERR_LLM_UNAVAILABLE`，列出所有尝试的错误 |
| LLM 调用超时 | 自动故障转移到下一个提供商 |
| 大型 DID 表（100+条） | 分批提取 + 汇总合并 |

---

## 9. 通用工具提取

以下组件具有高复用价值，可作为通用工具独立封装：

### 9.1 通用工具清单

| #   | 组件                       | 当前位置                                | 说明                                          |
| --- | ------------------------ | ----------------------------------- | ------------------------------------------- |
| 1   | **Excel 读取框架**           | `excel_framework/`                  | 智能Sheet过滤、文本转换、值归一化，可服务于任何"Excel→LLM"场景     |
| 2   | **LLM 网关客户端**            | `llm_client.py`                     | 多提供商故障转移、健康检查、重试策略，可独立为 LLM 调用中间件           |
| 3   | **JSON 响应解析器**           | `response_parser.py`                | 处理 LLM 输出的各种 JSON 变体（代码块包裹、前后文字、嵌套括号），通用性极强 |
| 4   | **提示词管理框架**              | `prompt_loader.py` + `prompts/`     | 多层提示词组装 + 动态参数注入，可泛化为"提示词即配置"的通用框架          |
| 7   | **MCP Server（Excel解析）**  | 已集成                                 | Model Context Protocol 服务器，提供标准化 Excel 解析接口 |
| 8   | **Excel 导出引擎**           | `excel_export.py`                   | 结构化数据 → 格式化 Excel 输出，含合并单元格、样式              |

---

## 10. 提示词资产清单

### 10.1 提示词文件列表

| 文件 | 内容 | 估算 Token | 硬编码类别 |
| --- | --- | --- | --- |
| `prompts/service_0x10_prompt.md` | 0x10 规则（已拆分，仅含 0x10） | ~5,200 | session_layer, sprmib, secure_access, incorrect_command, nrc_priority, subfunction_traversal |
| `prompts/service_0x11_prompt.md` | 0x11 规则（独立文件） | ~3,700 | session_layer, sprmib, secure_access, incorrect_command, subfunction_traversal |
| `prompts/service_0x14_prompt.md` | 0x14 规则（4分类） | ~2,300 | session_layer, sprmib, secure_access, incorrect_command |
| `prompts/service_0x19_prompt.md` | 0x19 规则（5子功能） | ~3,700 | session_layer, sprmib, secure_access, incorrect_command, subfunction_traversal |
| `prompts/service_0x22_prompt.md` | 0x22 规则（DID遍历） | ~3,100 | session_layer, sprmib, secure_access, incorrect_command, subfunction_traversal, did_range |
| `prompts/service_0x27_prompt.md` | 0x27 规则（8分类） | ~4,200 | session_layer, sprmib, secure_access, incorrect_command, subfunction_traversal |
| `prompts/service_0x28_prompt.md` | 0x28 规则（双遍历） | ~4,000 | session_layer, sprmib, secure_access, incorrect_command, subfunction_traversal |
| `prompts/service_0x2E_prompt.md` | 0x2E 规则（写DID） | ~1,700 | session_layer, sprmib, secure_access, incorrect_command, subfunction_traversal |
| `prompts/service_0x31_prompt.md` | 0x31 规则（RID条件） | ~2,400 | session_layer, sprmib, secure_access, incorrect_command, subfunction_traversal |
| `prompts/service_0x3E_prompt.md` | 0x3E 规则（S3定时器） | ~3,400 | session_layer, sprmib, secure_access, incorrect_command, subfunction_traversal |
| `prompts/service_0x85_prompt.md` | 0x85 规则（DTC开关） | ~3,000 | session_layer, sprmib, secure_access, incorrect_command, subfunction_traversal |
| `prompts/extract_prompt.md` | LLM 参数提取系统提示词（含 DTC 触发方法） | ~1,400 | — |
| **提示词资产总计** | | **~38,100** | |

### 10.2 3层提示词组装结构

```
Layer 1: SERVICE PROMPT (每个服务独立，~1,700 ~ 5,200 tokens)
  ├─ 服务概述（SID/正负响应格式/子功能/典型NRC）
  ├─ [HARDCODED] 分类标记（<!-- HARDCODED --> 标注模板生成器负责的类别）
  ├─ [LLM] 服务特有分类（如 ecu_reset、s3_timer、clear_dtc_function）
  └─ [LLM] 复杂逻辑分类（需 LLM 理解业务规则的类别）

Layer 2: ECU 参数注入（动态生成，~500 ~ 3,000 tokens）
  ├─ ECU 基本参数表（含 P2/P2* hex 编码值和转换公式）
  ├─ NRC 优先级链
  ├─ App 域服务支持矩阵（Markdown 表格）
  ├─ Boot 域服务支持矩阵（如存在）
  ├─ 安全访问映射表（Seed/Key 子功能对）
  ├─ ECU Reset 子功能列表
  ├─ DID/RID/DTC 列表（按需，DTC 含触发/恢复方法）
  └─ 输出格式模板（动态 hex 值）

Layer 3: 生成指令 + 输出格式约束（混合生成模式）
  ├─ 类别限制指令（仅请求 LLM_CATEGORIES 中的类别，排除硬编码类别）
  ├─ Case ID 起始编号（next_phy_id / next_fun_id，接续模板生成器）
  └─ 输出格式硬性约束（Case ID、Steps、Expected Output 三字段）
```

---

## 11. 文件与资产交付清单

### 11.1 代码文件

| 文件 | 职责 | 实际代码行数 |
| --- | --- | --- |
| `src/uds_agent/api.py` | FastAPI 后端 + 嵌入式 SPA 前端 | 627 行 |
| `src/uds_agent/template_generator.py` | 硬编码模板用例生成（新增） | 902 行 |
| `src/uds_agent/generate_pipeline.py` | 生成管道编排（含合并重编号） | 329 行 |
| `src/uds_agent/pipeline.py` | 提取管道编排 | 141 行 |
| `src/uds_agent/llm_client.py` | 多提供商 LLM 网关 | 275 行 |
| `src/uds_agent/prompt_loader.py` | 提示词组装 + 混合生成支持 | 273 行 |
| `src/uds_agent/test_parser.py` | 测试用例文本解析 | 425 行 |
| `src/uds_agent/excel_export.py` | Excel 导出 | 204 行 |
| `src/uds_agent/extract_prompt.py` | 提取提示词构建 | 54 行 |
| `src/uds_agent/response_parser.py` | LLM JSON 响应解析 | 75 行 |
| `src/uds_agent/schemas.py` | 提取结果 Pydantic 模型（含 DTC 触发方法） | 99 行 |
| `src/uds_agent/test_schemas.py` | 测试用例 Pydantic 模型 | 53 行 |
| `src/excel_framework/reader.py` | Excel 文件读取 | 164 行 |
| `src/excel_framework/text_converter.py` | 文本转换 + Sheet 过滤 | 110 行 |
| `src/excel_framework/value_normalizer.py` | 值归一化 | 69 行 |
| **合计** | | **~3,800 行** |

### 11.2 配置文件

| 文件 | 职责 |
| --- | --- |
| `config.yaml` | 提供商配置 + 故障转移策略 + 生成参数 + 服务提示词映射 |

### 11.3 提示词文件

共 12 个 Markdown 文件（见第 10.1 节）。其中 `service_0x10_prompt.md` 已拆分为仅含 0x10 规则，`service_0x11_prompt.md` 已独立为完整文件。所有服务提示词均已标记 `<!-- HARDCODED -->` 类别。

---

## 12. 部署方案

### 12.1 集成部署

```
集成部署:
  Python 环境 (3.10+)
    ├── FastAPI 应用 (uvicorn)
    │   ├── 后端 API（独立部署）
    │   └── 嵌入式泰能前端
    ├── 提示词文件 (prompts/)
    └── config.yaml

  LLM 服务（云端 API）
    ├── OpenRouter（国际线路，多模型可选）
    ├── Kimi（国内直连）
    └── DeepSeek（国内直连）
```

---


## 13. 验证方案

### 13.1 阶段一：管道打通验证

| 验证项 | 方法 | 通过标准 |
| --- | --- | --- |
| Excel 文本转换 | 用实际参数表输入 | 所有 Sheet 成功转文本 |
| LLM 参数提取 | 提取 0x10 参数 | JSON 格式正确，basic_info 和双域矩阵字段齐全 |
| 提取准确性 | 对比人工解读 | P2/P2* hex 值、安全访问映射、NRC 优先级链正确 |

### 13.2 阶段二：单服务生成验证

| 验证项 | 方法 | 通过标准 |
| --- | --- | --- |
| 0x10 用例生成 | 输入参数 → 生成 0x10 全部用例 | 用例数量 ≈ 已有 52 条（±10%） |
| 用例格式 | 检查 Case ID / 步骤 / Check | 格式 100% 符合模板 |
| 规则准确性 | 随机抽 10 条与人工输出对比 | 单条准确率 ≥ 90% |

### 13.3 阶段三：全服务回归验证

| 验证项 | 方法 | 通过标准 |
| --- | --- | --- |
| 全部 11 个服务 | 批量生成 | 无报错，所有服务都有输出 |
| 总量对比 | 生成总量 vs 已有 478 条 | 总量偏差 < 20% |
| 准确率 | 随机抽 20% 人工比对 | 准确率 ≥ 95% |

### 13.4 阶段四：格式适应性验证

| 验证项 | 方法 | 通过标准 |
| --- | --- | --- |
| 不同格式 Excel | 用其他项目参数表 | 能提取出基本参数 |
| 精简输入 | 用删减后输入 | 端到端生成成功 |
| 格式变化容忍 | 调整 Sheet 名/列顺序 | 仍能正确提取 |

---

## 14. 风险与应对

| 风险                    | 影响            | 应对                                     |
| --------------------- | ------------- | -------------------------------------- |
| LLM 参数提取 JSON 格式偶尔错误  | 管道中断          | 自动重试 + temperature 微调 + 宽松校验模式         |
| 大型 DID 表（100+条）超出模型精度 | 遗漏部分 DID      | 分批提取 + 汇总合并                            |
| 所有 LLM 提供商不可用         | 系统无法工作        | 多提供商故障转移（OpenRouter → DeepSeek → Qwen） |
| 输入 Excel 异常格式         | 读取异常          | 前置校验 + 友好错误提示                          |
| 提示词规则与客户规范不一致         | 生成用例不合规       | 提示词溯源表 + 变更时精准定位更新                     |
| 多用户并发场景性能瓶颈           | 响应慢           | 引入任务队列 + Redis 缓存                      |
| 提示词规则不全               | 降低生成用例覆盖率和准确率 | 结合业务部门输出调优提示词                          |

---

## 15. 未来拓展方向

### 15.1 短期（1-3 个月）

#### 15.1.1 多项目参数管理

- 支持 ECU 参数表版本管理
- 同一 ECU 不同软件版本的差异对比
- 项目模板化：新项目基于模板快速配置
#### 15.1.2 测试脚本自动生成

从测试用例文本自动生成 CAPL 脚本：

```
测试用例文本 → LLM → CAPL 脚本 (.can) → CANoe 直接执行
```

价值：打通"参数→用例→脚本→执行"全链路，进一步缩短测试周期。

### 15.2 中期（3-6 个月）

#### 15.2.1 生成质量自动评估

- 引入"LLM-as-Judge"自动评估生成用例质量
- 与人工标注的黄金标准自动比对
- 回归测试自动化：每次提示词更新后自动跑全服务验证

#### 15.2.2 本地模型部署

- vLLM + Qwen3-32B 或 DeepSeek-V3 本地部署
- 数据不出内网，满足信息安全要求
- 降低 API 调用成本

#### 15.2.3 通用工具包发布

将第 9 节识别的通用工具独立封装：

```
uds-assistant-toolkit/
├── excel_ingestion/     # Excel→Text 通用读取框架
├── llm_gateway/         # 多提供商 LLM 网关
├── output_parser/       # LLM 输出解析器
└── prompt_framework/    # 提示词管理框架
```

### 15.3 长期（6-12 个月）

#### 15.3.1 Agent 化演进

从当前固定管道演进为自主 Agent：

```
当前: 固定管道（Excel → 提取 → 生成 → 导出）
      用户需要手动上传、选择服务、检查结果

未来: 自主 Agent
      - 自动检测 Excel 中包含哪些服务
      - 自动识别格式差异并适配
      - 生成后自动校验，发现问题自动修复
      - 与 CANoe 集成，自动执行并收集结果
      - 根据执行结果自动补充遗漏用例
```

关键技术：Function Calling + ReAct 推理 + 工具集成（Excel 解析、LLM 调用、CANoe API）。
[[UDS技术验证报告_20260423_v1.0]]