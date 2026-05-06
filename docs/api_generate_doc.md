# UDS 测试用例生成接口文档

## 1. 生成接口

### POST /api/generate

异步生成测试用例。校验通过后立即返回，后台处理完成后通过回调接口通知结果。

#### 请求

- **Content-Type**: `multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | MultipartFile | 是 | ECU 诊断参数 Excel 文件（.xlsx / .xls） |
| `services` | String | 是 | 逗号分隔的服务 ID，如 `0x10,0x11` |
| `id` | String | 是 | 请求标识，由调用方传入，回调时原样返回 |

#### 响应（HTTP 202）

```json
{
  "id": "test-001",
  "code": "success",
  "message": "请求已接收，处理完成后将回调通知"
}
```

#### 错误码

| 状态码 | 说明 |
|--------|------|
| 400 | 未提供文件、文件格式不对、未指定服务、服务 ID 不支持 |
| 500 | 未配置回调地址 |

#### Java 调用示例

```java
RestTemplate restTemplate = new RestTemplate();
HttpHeaders headers = new HttpHeaders();
headers.setContentType(MediaType.MULTIPART_FORM_DATA);

MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
body.add("file", new FileSystemResource(new File("data.xlsx")));
body.add("services", "0x10,0x11");
body.add("domain", "App");
body.add("id", "test-001");

HttpEntity<MultiValueMap<String, Object>> request = new HttpEntity<>(body, headers);
ResponseEntity<String> response = restTemplate.postForEntity(
    "http://localhost:8000/api/generate", request, String.class
);
```

---

## 2. 回调接口

处理完成后，向 `config.yaml` 中 `callback.url` 配置的地址发送 POST 请求。

- **Content-Type**: `multipart/form-data`
- **请求方式**: POST（由 UDS Assistant 主动调用）

#### 请求参数

| 字段 | 类型 | 说明 |
|------|------|------|
| `data` | String (JSON) | 生成结果（见下方结构） |
| `file` | MultipartFile | 生成的 Excel 文件（全部失败时无此字段） |

#### data 字段结构

```json
{
  "id": "test-001",
  "status": "completed",
  "ecu_info": {
    "provider": "openrouter",
    "model": "anthropic/claude-opus-4.6"
  },
  "services": [
    {
      "service_id": "0x10",
      "service_name": "DiagnosticSessionControl",
      "sheet_name": "0x10_DiagnosticSessionControl",
      "total_count": 30,
      "test_cases": [
        {
          "section": "1. Application Service_Physical Addressing",
          "subsection": "1.1 Session Layer Test",
          "sequence_number": 1,
          "case_id": "Diag_0x10_Phy_001",
          "case_name": "Service 0x10 Default To Default",
          "priority": "High",
          "author": "Percy",
          "design_method": "Based on analysis of requirements",
          "precondition": "1.Power On;",
          "system_requirement_id": "1.General\n2.DiagnosticServices",
          "test_procedure": "1.Send DiagBy[Physical]Data[10 01];\n2.Send DiagBy[Physical]Data[10 01];",
          "expected_output": "1.Check DiagData[50 01 00 32 01 F4]Within[50]ms;\n2.Check DiagData[50 01 00 32 01 F4]Within[50]ms;"
        }
      ],
      "sections_summary": [],
      "meta": {
        "provider": "openrouter",
        "model": "anthropic/claude-opus-4.6",
        "elapsed_seconds": 200.6,
        "llm_tokens": 131308
      }
    }
  ],
  "meta": {
    "total_services": 2,
    "success_count": 2,
    "error_count": 0,
    "errors": [],
    "total_elapsed_seconds": 350.2
  }
}
```

#### data 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | String | 调用方传入的请求标识 |
| `status` | String | `completed`（全部成功）/ `partial`（部分失败）/ `failed`（全部失败） |
| `ecu_info` | Object | ECU 信息，包含 `provider` 和 `model` |
| `services` | Array | 各服务的生成结果（见 services 元素说明） |
| `meta.total_services` | Integer | 请求的服务总数 |
| `meta.success_count` | Integer | 成功的服务数 |
| `meta.error_count` | Integer | 失败的服务数 |
| `meta.errors` | Array | 失败详情，每项含 `service_id` 和 `error` |
| `meta.total_elapsed_seconds` | Number | 总耗时（秒） |

#### services 元素说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `service_id` | String | 服务 ID，如 `0x10` |
| `service_name` | String | 服务名称，如 `DiagnosticSessionControl` |
| `sheet_name` | String | Excel Sheet 名称 |
| `total_count` | Integer | 生成的测试用例总数 |
| `test_cases` | Array | 测试用例列表（见 test_cases 元素说明） |
| `sections_summary` | Array | 章节统计汇总 |
| `meta` | Object | 元信息，含 `provider`、`model`、`elapsed_seconds`、`llm_tokens` |

#### test_cases 元素说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `section` | String | 一级分类，如 `1. Application Service_Physical Addressing` |
| `subsection` | String | 二级分类，如 `1.1 Session Layer Test` |
| `sequence_number` | Integer | 序号 |
| `case_id` | String | 用例 ID，如 `Diag_0x10_Phy_001` |
| `case_name` | String | 用例名称 |
| `priority` | String | 优先级：`High` / `Medium` / `Low` |
| `author` | String | 作者 |
| `design_method` | String | 设计方法 |
| `precondition` | String | 前置条件 |
| `system_requirement_id` | String | 系统需求 ID |
| `test_procedure` | String | 测试步骤 |
| `expected_output` | String | 预期输出 |

#### file 字段

- **文件名格式**: `{原文件名}_{yyyyMMddHHmmss}.xlsx`
- 全部服务生成失败时不发送此字段

#### Java 接收示例

```java
@RestController
public class CallbackController {

    @PostMapping("/api/callback")
    public Map<String, String> handleCallback(
            @RequestPart("data") String data,
            @RequestPart(value = "file", required = false) MultipartFile file) {

        JSONObject result = JSON.parseObject(data);
        String id = result.getString("id");
        String status = result.getString("status");
        log.info("收到回调: id={}, status={}", id, status);

        if ("completed".equals(status) || "partial".equals(status)) {
            // 保存 Excel 文件
            if (file != null && !file.isEmpty()) {
                String filename = file.getOriginalFilename();
                file.transferTo(new File("/path/to/save/" + filename));
            }

            // 解析测试用例数据
            JSONArray services = result.getJSONArray("services");
            for (int i = 0; i < services.size(); i++) {
                JSONObject svc = services.getJSONObject(i);
                JSONArray testCases = svc.getJSONArray("test_cases");
                // 处理测试用例...
            }
        }

        return Map.of("code", "success");
    }
}
```

---

## 3. 支持的服务列表

| 服务 ID | 服务名称 |
|---------|----------|
| 0x10 | DiagnosticSessionControl |
| 0x11 | ECUReset |
| 0x14 | ClearDiagnosticInformation |
| 0x19 | ReadDTCInformation |
| 0x22 | ReadDataByIdentifier |
| 0x27 | SecurityAccess |
| 0x28 | CommunicationControl |
| 0x2E | WriteDataByIdentifier |
| 0x31 | RoutineControl |
| 0x3E | TesterPresent |
| 0x85 | ControlDTCSettings |
