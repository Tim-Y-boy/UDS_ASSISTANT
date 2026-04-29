"""模块三：测试用例生成管道。Excel → 提取参数 → LLM 生成用例 → 解析输出。"""

from __future__ import annotations

import logging
import time

from .llm_client import LLMClient, LLMResponse
from .pipeline import ExtractionOutput, UDSExtractionPipeline
from .prompt_loader import (
    SERVICE_NAMES,
    build_generation_user_message,
    build_sheet_name,
    load_generation_config,
    load_service_prompt,
)
from .schemas import ValidationReport
from .test_parser import parse_summary, parse_test_cases
from .test_schemas import ServiceTestResult

logger = logging.getLogger("generate_pipeline")


def _serialize_validation_report(report: ValidationReport | None) -> dict:
    if report is None:
        return {"findings": [], "auto_fixes_applied": 0}
    return {
        "findings": [
            {
                "rule_id": f.rule_id,
                "severity": f.severity,
                "message": f.message,
                "field_path": f.field_path,
                "auto_fixed": f.auto_fixed,
                "old_value": f.old_value,
                "new_value": f.new_value,
            }
            for f in report.findings
        ],
        "auto_fixes_applied": report.auto_fixes_applied,
        "tier1_duration_ms": report.tier1_duration_ms,
        "tier2_duration_ms": report.tier2_duration_ms,
    }


def _build_diagnostics(
    extraction: ExtractionOutput,
    llm_response: LLMResponse | None,
    total_elapsed: float,
) -> dict:
    r = extraction.result
    bi = r.basic_info
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
        "extraction_llm": {
            "provider": extraction.provider_used,
            "model": extraction.model_used,
            "usage": extraction.llm_usage,
        },
        "extraction_counts": {
            "app_subfunctions": len(r.service_matrix.subfunctions),
            "boot_subfunctions": len(r.boot_matrix.subfunctions) if r.boot_matrix else 0,
            "did_count": len(r.did_list),
            "dtc_count": len(r.dtc_list),
            "routine_count": len(r.routine_list),
            "security_levels": len(r.security_list),
            "reset_subfunctions": len(r.reset_subfunctions),
        },
        "basic_info_summary": {
            "ecu_name": bi.ecu_name,
            "p2_ms": bi.p2_ms,
            "p2star_ms": bi.p2star_ms,
            "s3_ms": bi.s3_ms,
            "canid_req": bi.canid_req,
            "canid_resp": bi.canid_resp,
        },
        "validation": _serialize_validation_report(extraction.validation_report),
        "errors": extraction.errors,
    }


class UDSGeneratePipeline:
    """完整生成管道：提取参数 → 加载提示词 → LLM 生成 → 解析输出。"""

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
    ) -> ServiceTestResult:
        """执行完整的生成管道。同时提取 App+Boot 双域参数。"""
        start = time.time()

        # 1. 提取参数（同时提取 App+Boot 双域）
        logger.info(f"[{service_id}] 开始提取参数（App+Boot 双域）...")
        extraction = self._extract_pipeline.extract(
            excel_path=excel_path,
            service_id=service_id,
            software_domain=domain,
        )

        if extraction.errors:
            logger.warning(f"[{service_id}] 提取有错误: {extraction.errors}")

        has_boot = (
            extraction.result.boot_matrix
            and extraction.result.boot_matrix.subfunctions
        )
        logger.info(
            f"[{service_id}] 提取完成: App={len(extraction.result.service_matrix.subfunctions)} 子功能"
            f"{f', Boot={len(extraction.result.boot_matrix.subfunctions)} 子功能' if has_boot else ', 无 Boot 域'}"
            f", Security={len(extraction.result.security_list)}"
            f", Reset={len(extraction.result.reset_subfunctions)}"
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

        # 3. 构建 user message（生成全部类别）
        user_message = build_generation_user_message(
            extraction.result, service_id,
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

        # 5. 解析输出
        test_cases = parse_test_cases(llm_response.content, service_id)
        summary = parse_summary(llm_response.content)

        # 6. 填充配置字段
        author = self._gen_config.get("author", "Percy")
        design_method = self._gen_config.get("design_method", "Based on analysis of requirements")
        precondition = self._gen_config.get("precondition", "1.Power On;")
        sys_req_id = self._gen_config.get("system_requirement_id", "1.General\n2.DiagnosticServices")

        for tc in test_cases:
            tc.author = author
            tc.design_method = design_method
            tc.precondition = precondition
            tc.system_requirement_id = sys_req_id

        elapsed = time.time() - start
        logger.info(
            f"[{service_id}] 生成完成: {len(test_cases)} 条用例, {elapsed:.1f}s"
        )

        # 从提取结果或配置映射获取 service_name
        sid_key = service_id.lower()
        service_name = (
            extraction.result.service_matrix.service_name
            or SERVICE_NAMES.get(sid_key, "")
        )

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
                "extraction_warnings": extraction.validation_warnings,
                "extraction_diagnostics": _build_diagnostics(extraction, llm_response, elapsed),
            },
        )
