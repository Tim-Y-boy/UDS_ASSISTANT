"""模块1+2 管道编排：Excel → 文本 → LLM → 结构化参数。"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from ..excel_framework import ExcelReader, SheetTextConverter
from .extract_prompt import build_extraction_messages
from .llm_client import LLMClient, LLMResponse
from .response_parser import parse_json_response, validate_extraction
from .schemas import FullExtractionResult, ValidationReport

logger = logging.getLogger("pipeline")


@dataclass
class ExtractionOutput:
    """提取管道的完整输出。"""

    result: FullExtractionResult
    raw_llm_response: str = ""
    llm_usage: dict = field(default_factory=dict)
    validation_warnings: list[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)
    excel_text_length: int = 0
    sheets_filtered: list[str] = field(default_factory=list)
    provider_used: str = ""
    model_used: str = ""
    validation_report: ValidationReport | None = None


class UDSExtractionPipeline:
    """Excel → LLM → 结构化参数 的完整管道。"""

    def __init__(
        self,
        config_path: str = "config.yaml",
        task: str = "extract",
    ):
        self._client = LLMClient.from_config(config_path=config_path, task=task)
        self._config_path = config_path

    def extract(
        self,
        excel_path: str,
        service_id: str,
        software_domain: str = "App",
    ) -> ExtractionOutput:
        """执行完整的提取管道。"""
        start = time.time()
        errors: list[str] = []
        warnings: list[str] = []

        # 1. 读取 Excel
        try:
            reader = ExcelReader(excel_path)
            sheets = reader.read_all_sheets()
        except FileNotFoundError as e:
            return ExtractionOutput(
                result=FullExtractionResult(),
                errors=[f"ERR_FILE_INVALID: {e}"],
                elapsed_seconds=time.time() - start,
            )
        except Exception as e:
            return ExtractionOutput(
                result=FullExtractionResult(),
                errors=[f"ERR_FILE_INVALID: {e}"],
                elapsed_seconds=time.time() - start,
            )

        # 2. 转换为文本（带智能过滤）
        converter = SheetTextConverter()
        all_names = list(sheets.keys())
        filtered_names = converter.filter_relevant_sheets(all_names)
        excel_text = converter.convert_workbook(sheets, filter_sheets=True)

        # 3. 构建提示词
        try:
            system_prompt, user_message = build_extraction_messages(
                excel_text=excel_text,
                service_id=service_id,
                software_domain=software_domain,
                prompts_dir="prompts",
            )
        except FileNotFoundError as e:
            return ExtractionOutput(
                result=FullExtractionResult(),
                errors=[str(e)],
                elapsed_seconds=time.time() - start,
                excel_text_length=len(excel_text),
                sheets_filtered=filtered_names,
            )

        # 4. 调用 LLM（自动故障转移）
        try:
            llm_resp: LLMResponse = self._client.chat(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.05,
                max_tokens=8000,
            )
        except RuntimeError as e:
            return ExtractionOutput(
                result=FullExtractionResult(),
                errors=[f"ERR_LLM_UNAVAILABLE: {e}"],
                elapsed_seconds=time.time() - start,
                excel_text_length=len(excel_text),
                sheets_filtered=filtered_names,
            )

        # 5. 解析 JSON
        try:
            data = parse_json_response(llm_resp.content)
        except ValueError as e:
            return ExtractionOutput(
                result=FullExtractionResult(),
                raw_llm_response=llm_resp.content,
                errors=[f"ERR_LLM_PARSE_FAIL: {e}"],
                elapsed_seconds=time.time() - start,
                excel_text_length=len(excel_text),
                sheets_filtered=filtered_names,
            )

        # 6. Pydantic 校验
        result, val_warnings = validate_extraction(data)
        warnings.extend(val_warnings)

        # 6b. 提取结果验证（自动修复 + 两层校验）
        from .extraction_validator import ExtractionValidator, format_findings
        validator = ExtractionValidator(excel_path=excel_path)
        report = validator.validate(result)
        warnings.extend(format_findings(report))

        return ExtractionOutput(
            result=result,
            raw_llm_response=llm_resp.content,
            llm_usage=llm_resp.usage,
            validation_warnings=warnings,
            elapsed_seconds=time.time() - start,
            errors=errors,
            excel_text_length=len(excel_text),
            sheets_filtered=filtered_names,
            provider_used=llm_resp.provider,
            model_used=llm_resp.model,
            validation_report=report,
        )
