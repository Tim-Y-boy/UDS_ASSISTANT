"""测试用例生成管道。Excel → 文本 → LLM 直接生成用例 → 解析输出。"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from .llm_client import LLMClient, LLMResponse
from .pipeline import ExtractionOutput, UDSExtractionPipeline
from .prompt_loader import (
    SERVICE_NAMES,
    build_generation_user_message,
    build_sheet_name,
    load_generation_config,
    load_service_prompt,
)
from .test_parser import parse_summary, parse_test_cases
from .test_schemas import ServiceTestResult

logger = logging.getLogger("generate_pipeline")

_LOG_DIR = Path(__file__).parent.parent.parent / "logs"


def _build_diagnostics(
    extraction: ExtractionOutput,
    llm_response: LLMResponse | None,
    total_elapsed: float,
) -> dict:
    return {
        "timing": {
            "extraction_seconds": round(extraction.elapsed_seconds, 2),
            "generation_seconds": round(llm_response.elapsed_seconds, 2) if llm_response else 0,
            "total_seconds": round(total_elapsed, 2),
        },
        "excel_input": {
            "text_length": extraction.excel_text_length,
            "sheets_filtered": extraction.sheets_filtered,
        },
        "errors": extraction.errors,
    }


class UDSGeneratePipeline:
    """生成管道：读取 Excel 文本 → 加载提示词 → LLM 生成 → 解析输出。"""

    def __init__(self, config_path: str = "config.yaml"):
        self._extract_pipeline = UDSExtractionPipeline(config_path=config_path)
        self._generate_client = LLMClient.from_config(
            config_path=config_path, task="generate"
        )
        self._config_path = config_path
        self._gen_config = load_generation_config(config_path)

    def generate(
        self,
        excel_path: str,
        service_id: str,
        domain: str = "App",
        original_filename: str = "",
    ) -> ServiceTestResult:
        """执行完整的生成管道。"""
        start = time.time()

        # 1. 读取 Excel 文本
        logger.info(f"[{service_id}] 读取 Excel 文本...")
        extraction = self._extract_pipeline.extract(
            excel_path=excel_path,
            service_id=service_id,
            software_domain=domain,
            original_filename=original_filename,
        )

        if extraction.errors:
            logger.warning(f"[{service_id}] Excel 读取有错误: {extraction.errors}")

        logger.info(
            f"[{service_id}] Excel 文本长度: {extraction.excel_text_length} 字符"
        )

        # 2. 加载服务提示词
        try:
            service_prompt = load_service_prompt(service_id, self._config_path)
        except FileNotFoundError as e:
            elapsed_err = time.time() - start
            return ServiceTestResult(
                service_id=service_id,
                service_name=SERVICE_NAMES.get(service_id.lower(), ""),
                sheet_name=build_sheet_name(service_id),
                meta={
                    "error": str(e),
                    "elapsed_seconds": elapsed_err,
                    "extraction_diagnostics": _build_diagnostics(extraction, None, elapsed_err),
                },
            )

        # 3. 构建 user message（直接使用 Excel 原始文本）
        user_message = build_generation_user_message(
            excel_text=extraction.excel_text,
            service_id=service_id,
        )

        logger.info(
            f"[{service_id}] 提示词加载完成，user message 长度: {len(user_message)}"
        )

        # 4. 调用 LLM 生成用例
        llm_response: LLMResponse | None = None
        max_tokens = self._gen_config.get("max_tokens", 32000)

        try:
            llm_response = self._generate_client.chat(
                system_prompt=service_prompt,
                user_message=user_message,
                temperature=0.05,
                max_tokens=max_tokens,
            )
            logger.info(
                f"[{service_id}] LLM 生成完成 ({llm_response.elapsed_seconds:.1f}s, "
                f"{llm_response.usage.get('total_tokens', 0)} tokens)"
            )
        except RuntimeError as e:
            logger.error(f"[{service_id}] LLM 不可用: {e}")
            elapsed_err = time.time() - start
            return ServiceTestResult(
                service_id=service_id,
                service_name=SERVICE_NAMES.get(service_id.lower(), ""),
                sheet_name=build_sheet_name(service_id),
                meta={
                    "error": str(e),
                    "elapsed_seconds": elapsed_err,
                    "extraction_diagnostics": _build_diagnostics(extraction, None, elapsed_err),
                },
            )

        # 5. 保存 LLM 原始输出（调试用）
        _LOG_DIR.mkdir(exist_ok=True)
        _raw_log = _LOG_DIR / f"llm_raw_{service_id}_{int(time.time())}.md"
        _raw_log.write_text(llm_response.content, encoding="utf-8")
        logger.info(f"[{service_id}] LLM 原始输出已保存: {_raw_log}")

        # 6. 解析输出
        test_cases = parse_test_cases(llm_response.content, service_id)
        summary = parse_summary(llm_response.content)

        # 6. 填充配置字段
        author = self._gen_config.get("author", "")
        design_method = self._gen_config.get("design_method", "")
        precondition = self._gen_config.get("precondition", "")
        sys_req_id = self._gen_config.get("system_requirement_id", "")

        for tc in test_cases:
            tc.author = author
            tc.design_method = design_method
            tc.precondition = precondition
            tc.system_requirement_id = sys_req_id

        elapsed = time.time() - start
        logger.info(
            f"[{service_id}] 生成完成: {len(test_cases)} 条用例, {elapsed:.1f}s"
        )

        sid_key = service_id.lower()
        service_name = SERVICE_NAMES.get(sid_key, "")

        return ServiceTestResult(
            service_id=service_id,
            service_name=service_name,
            sheet_name=build_sheet_name(service_id),
            total_count=len(test_cases),
            test_cases=test_cases,
            sections_summary=summary,
            meta={
                "provider": llm_response.provider if llm_response else "unknown",
                "model": llm_response.model if llm_response else "unknown",
                "elapsed_seconds": round(elapsed, 2),
                "llm_tokens": llm_response.usage.get("total_tokens", 0) if llm_response else 0,
                "extraction_diagnostics": _build_diagnostics(extraction, llm_response, elapsed),
            },
        )
