"""提取结果验证器：自动修复 + 自洽性检查 + Excel 交叉验证。"""

from __future__ import annotations

import logging
import re
import time

from .schemas import (
    FullExtractionResult,
    ValidationFinding,
    ValidationReport,
)

logger = logging.getLogger("extraction_validator")


class ExtractionValidator:
    """两层提取结果验证器，支持自动修复。"""

    def __init__(self, excel_path: str | None = None):
        self._excel_path = excel_path
        self._findings: list[ValidationFinding] = []

    def validate(self, result: FullExtractionResult) -> ValidationReport:
        """执行全部验证。先自动修复，再 Tier1 + Tier2 检查。"""
        self._findings = []

        # 自动修复（in-place）
        auto_fixes = self.apply_auto_fixes(result)

        # Tier 1：自洽性检查
        t1_start = time.perf_counter()
        self._run_tier1(result)
        t1_ms = (time.perf_counter() - t1_start) * 1000

        # Tier 2：Excel 交叉验证
        t2_ms = 0.0
        if self._excel_path:
            t2_start = time.perf_counter()
            self._run_tier2(result)
            t2_ms = (time.perf_counter() - t2_start) * 1000

        report = ValidationReport(
            findings=list(self._findings),
            auto_fixes_applied=auto_fixes,
            tier1_duration_ms=round(t1_ms, 1),
            tier2_duration_ms=round(t2_ms, 1),
        )

        logger.info(
            f"验证完成: {auto_fixes} 项自动修复, "
            f"{len(self._findings)} 条发现 "
            f"(Tier1={t1_ms:.0f}ms, Tier2={t2_ms:.0f}ms)"
        )
        return report

    # ------------------------------------------------------------------
    # 自动修复
    # ------------------------------------------------------------------

    def apply_auto_fixes(self, result: FullExtractionResult) -> int:
        """确定性修正，返回修复数量。"""
        fixes = 0
        bi = result.basic_info

        # P2 hex 重算
        if bi.p2_ms > 0:
            expected = f"{bi.p2_ms:04X}"
            if bi.p2_hex != expected:
                self._add_finding(
                    "T1_P2_HEX", "error",
                    f"P2 hex 不匹配: LLM=\"{bi.p2_hex}\", 正确=\"{expected}\" ({bi.p2_ms}ms)",
                    "basic_info.p2_hex", auto_fixed=True,
                    old_value=bi.p2_hex, new_value=expected,
                )
                bi.p2_hex = expected
                fixes += 1

        # P2* hex 重算
        if bi.p2star_ms > 0:
            expected = f"{bi.p2star_ms // 10:04X}"
            if bi.p2star_hex != expected:
                self._add_finding(
                    "T1_P2STAR_HEX", "error",
                    f"P2* hex 不匹配: LLM=\"{bi.p2star_hex}\", 正确=\"{expected}\" ({bi.p2star_ms}ms÷10)",
                    "basic_info.p2star_hex", auto_fixed=True,
                    old_value=bi.p2star_hex, new_value=expected,
                )
                bi.p2star_hex = expected
                fixes += 1

        # Hex 规范化：子功能补零
        for matrix in (result.service_matrix, result.boot_matrix):
            if not matrix:
                continue
            for sf in matrix.subfunctions:
                sub = sf.subfunction.strip()
                if len(sub) == 1 and re.match(r"[0-9A-Fa-f]$", sub):
                    sf.subfunction = sub.upper().zfill(2)

        # NRC 链清理
        if bi.nrc_priority_chain:
            chain = bi.nrc_priority_chain
            # 统一分隔符
            chain = chain.replace(",", ">")
            parts = [p.strip() for p in chain.split(">") if p.strip()]
            # 去除 "7F" 前缀（是响应 SID 前缀不是 NRC）
            cleaned = []
            for p in parts:
                p = p.upper()
                if p == "7F":
                    continue
                if not re.match(r"^[0-9A-F]{2}$", p):
                    continue
                if p not in cleaned:
                    cleaned.append(p)
            new_chain = ">".join(cleaned)
            if new_chain != bi.nrc_priority_chain:
                self._add_finding(
                    "T1_NRC_CHAIN_FORMAT", "info",
                    f"NRC 优先级链已规范化: \"{bi.nrc_priority_chain}\" → \"{new_chain}\"",
                    "basic_info.nrc_priority_chain", auto_fixed=True,
                    old_value=bi.nrc_priority_chain, new_value=new_chain,
                )
                bi.nrc_priority_chain = new_chain
                fixes += 1

        return fixes

    # ------------------------------------------------------------------
    # Tier 1：自洽性检查
    # ------------------------------------------------------------------

    def _run_tier1(self, result: FullExtractionResult) -> None:
        self._check_seed_key_pairing(result)
        self._check_subfunction_consistency(result)
        self._check_nrc_chain_completeness(result)
        self._check_did_format(result)
        self._check_dtc_format(result)
        self._check_security_match(result)

    def _check_seed_key_pairing(self, result: FullExtractionResult) -> None:
        """Seed 必须奇数，Key=Seed+1 必须偶数。"""
        for sec in result.security_list:
            try:
                seed = int(sec.seed_sub, 16)
                key = int(sec.key_sub, 16)
            except (ValueError, TypeError):
                self._add_finding(
                    "T1_SEED_KEY_PAIR", "error",
                    f"安全等级 {sec.level}: Seed/Key 子功能无法解析 (seed=\"{sec.seed_sub}\", key=\"{sec.key_sub}\")",
                    f"security_list[{sec.level}].seed_sub",
                )
                continue

            if seed % 2 == 0:
                self._add_finding(
                    "T1_SEED_KEY_PAIR", "error",
                    f"安全等级 {sec.level}: Seed 子功能 {sec.seed_sub} 应为奇数",
                    f"security_list[{sec.level}].seed_sub",
                )
            if key != seed + 1:
                self._add_finding(
                    "T1_SEED_KEY_PAIR", "error",
                    f"安全等级 {sec.level}: Key={sec.key_sub} 应为 Seed+1={seed + 1:02X}",
                    f"security_list[{sec.level}].key_sub",
                )

    def _check_subfunction_consistency(self, result: FullExtractionResult) -> None:
        """support=False 时不应有 session/寻址标志。"""
        for matrix in (result.service_matrix, result.boot_matrix):
            if not matrix:
                continue
            for sf in matrix.subfunctions:
                if not sf.support:
                    active_sessions = []
                    if sf.session_default:
                        active_sessions.append("Default")
                    if sf.session_extended:
                        active_sessions.append("Extended")
                    if sf.session_programming:
                        active_sessions.append("Programming")
                    if active_sessions:
                        self._add_finding(
                            "T1_SUBFUNC_CONSISTENCY", "warning",
                            f"子功能 {sf.subfunction} ({sf.subfunction_name}): support=False 但会话 [{', '.join(active_sessions)}] 为 True",
                            f"subfunctions[{sf.subfunction}].session_*",
                        )
                    if sf.sprmib:
                        self._add_finding(
                            "T1_SUBFUNC_CONSISTENCY", "warning",
                            f"子功能 {sf.subfunction} ({sf.subfunction_name}): support=False 但 SPRMIB=True",
                            f"subfunctions[{sf.subfunction}].sprmib",
                        )

    def _check_nrc_chain_completeness(self, result: FullExtractionResult) -> None:
        """子功能 NRC 码应覆盖 NRC 优先级链中的码。"""
        chain = result.basic_info.nrc_priority_chain
        if not chain:
            return
        chain_codes = set(chain.split(">"))

        all_sub_nrcs = set()
        for matrix in (result.service_matrix, result.boot_matrix):
            if not matrix:
                continue
            for sf in matrix.subfunctions:
                for nrc in sf.nrc_codes:
                    all_sub_nrcs.add(nrc.upper().strip())

        missing = chain_codes - all_sub_nrcs
        if missing:
            self._add_finding(
                "T1_NRC_CHAIN_FORMAT", "warning",
                f"NRC 优先级链 [{chain}] 中的 {missing} 未出现在任何子功能的 nrc_codes 中",
                "basic_info.nrc_priority_chain",
            )

    def _check_did_format(self, result: FullExtractionResult) -> None:
        """DID 格式校验。"""
        for i, did in enumerate(result.did_list):
            dn = did.did_number.strip()
            # 去除 0x 前缀后检查
            hex_val = dn.replace("0x", "").replace("0X", "").replace(" ", "")
            if not re.match(r"^[0-9A-Fa-f]{2,4}$", hex_val):
                self._add_finding(
                    "T1_DID_FORMAT", "warning",
                    f"DID[{i}] \"{dn}\" ({did.did_name}): 格式不是有效的 2-4 位 hex",
                    f"did_list[{i}].did_number",
                )
            if did.byte_length <= 0:
                self._add_finding(
                    "T1_DID_FORMAT", "warning",
                    f"DID[{i}] \"{dn}\": byte_length={did.byte_length}，应为正整数",
                    f"did_list[{i}].byte_length",
                )
            if not did.read_support and not did.write_support:
                self._add_finding(
                    "T1_DID_FORMAT", "warning",
                    f"DID[{i}] \"{dn}\": read_support=False 且 write_support=False，DID 不可用",
                    f"did_list[{i}].read_support",
                )

    def _check_dtc_format(self, result: FullExtractionResult) -> None:
        """DTC 格式校验。"""
        for i, dtc in enumerate(result.dtc_list):
            if not dtc.trigger_conditions:
                self._add_finding(
                    "T1_DTC_FORMAT", "warning",
                    f"DTC[{i}] \"{dtc.dtc_number}\" ({dtc.dtc_name}): trigger_conditions 为空，无法生成故障触发步骤",
                    f"dtc_list[{i}].trigger_conditions",
                )

    def _check_security_match(self, result: FullExtractionResult) -> None:
        """子功能 access_level 与 security_list 对应检查。"""
        if not result.security_list:
            return

        sec_levels = {sec.level for sec in result.security_list}

        for matrix in (result.service_matrix, result.boot_matrix):
            if not matrix:
                continue
            for sf in matrix.subfunctions:
                if sf.access_level and sf.access_level not in ("Level0", "L0", ""):
                    # 提取安全等级名称（如 "L2" → 检查 security_list 中是否存在）
                    level = sf.access_level.strip()
                    if level not in sec_levels:
                        self._add_finding(
                            "T1_SECURITY_MATCH", "warning",
                            f"子功能 {sf.subfunction} ({sf.subfunction_name}): access_level=\"{level}\" 不在 security_list [{', '.join(sec_levels)}] 中",
                            f"subfunctions[{sf.subfunction}].access_level",
                        )

    # ------------------------------------------------------------------
    # Tier 2：Excel 交叉验证
    # ------------------------------------------------------------------

    def _run_tier2(self, result: FullExtractionResult) -> None:
        """读取 Excel 比对提取数量。"""
        try:
            from ..excel_framework.reader import ExcelReader
        except ImportError:
            from excel_framework.reader import ExcelReader

        try:
            reader = ExcelReader(self._excel_path)
            sheets = reader.read_all_sheets()
        except Exception as e:
            logger.warning(f"Tier 2 无法读取 Excel: {e}")
            return

        detector = SheetDetector(sheets)

        # DID 数量比对
        excel_did_count = detector.count_unique_dids()
        if excel_did_count is not None:
            llm_did_count = len(result.did_list)
            if llm_did_count < excel_did_count:
                self._add_finding(
                    "T2_DID_COUNT", "warning",
                    f"DID 数量不一致: LLM提取={llm_did_count}, Excel实际={excel_did_count}, 缺少{excel_did_count - llm_did_count}个",
                    "did_list",
                )
            elif llm_did_count > excel_did_count:
                self._add_finding(
                    "T2_DID_COUNT", "info",
                    f"DID 数量: LLM提取={llm_did_count}, Excel实际={excel_did_count}, LLM 多提取{llm_did_count - excel_did_count}个（可能包含跨 sheet 合并）",
                    "did_list",
                )

        # 子功能数量比对
        excel_sub_count = detector.count_subfunctions()
        if excel_sub_count is not None:
            llm_sub_count = len(result.service_matrix.subfunctions)
            if llm_sub_count != excel_sub_count:
                self._add_finding(
                    "T2_SUBFUNC_COUNT", "warning",
                    f"App 域子功能数量不一致: LLM提取={llm_sub_count}, Excel实际={excel_sub_count}",
                    "service_matrix.subfunctions",
                )

        # DTC 数量比对
        excel_dtc_count = detector.count_unique_dtcs()
        if excel_dtc_count is not None:
            llm_dtc_count = len(result.dtc_list)
            if llm_dtc_count != excel_dtc_count:
                self._add_finding(
                    "T2_DTC_COUNT", "warning",
                    f"DTC 数量不一致: LLM提取={llm_dtc_count}, Excel实际={excel_dtc_count}",
                    "dtc_list",
                )

        # RID 数量比对
        excel_rid_count = detector.count_unique_rids()
        if excel_rid_count is not None:
            llm_rid_count = len(result.routine_list)
            if llm_rid_count != excel_rid_count:
                self._add_finding(
                    "T2_ROUTINE_COUNT", "warning",
                    f"RID 数量不一致: LLM提取={llm_rid_count}, Excel实际={excel_rid_count}",
                    "routine_list",
                )

    # ------------------------------------------------------------------
    # 辅助
    # ------------------------------------------------------------------

    def _add_finding(
        self,
        rule_id: str,
        severity: str,
        message: str,
        field_path: str,
        *,
        auto_fixed: bool = False,
        old_value: str = "",
        new_value: str = "",
    ) -> None:
        self._findings.append(ValidationFinding(
            rule_id=rule_id,
            severity=severity,
            message=message,
            field_path=field_path,
            auto_fixed=auto_fixed,
            old_value=old_value,
            new_value=new_value,
        ))


# ======================================================================
# SheetDetector：格式容忍的 Excel 数据计数
# ======================================================================

_HEX_PATTERN = re.compile(r"^[0-9A-Fa-f]{2,8}$")


class SheetDetector:
    """按语义匹配检测 sheet 类型，统计实际数据行数。"""

    DID_KEYWORDS = ["did", "rdbi", "wdbi", "03.1", "03.2", "03.3"]
    SERVICE_KEYWORDS = ["diagnostic services", "applicationservices", "bootservices", "02.1", "02.2", "02.3"]
    DTC_KEYWORDS = ["dtc", "04.1", "04.2", "groupofdtc"]
    ROUTINE_KEYWORDS = ["routine", "0x31", "03.5"]

    def __init__(self, sheets: dict):
        """sheets: ExcelReader.read_all_sheets() 的返回值。"""
        self._sheets = sheets

    def _find_sheets(self, keywords: list[str]) -> list[tuple[str, object]]:
        """返回匹配关键词的 (sheet_name, SheetData) 列表。"""
        matched = []
        for name, data in self._sheets.items():
            name_lower = name.lower()
            if any(kw in name_lower for kw in keywords):
                matched.append((name, data))
        return matched

    def _find_did_column(self, rows: list[list], max_search_rows: int = 6) -> int | None:
        """在前几行中搜索 DID 编号列。"""
        patterns = ["did", "hex", "did号", "did number"]
        return self._find_column_by_patterns(rows, patterns, max_search_rows)

    def _find_rid_column(self, rows: list[list], max_search_rows: int = 6) -> int | None:
        patterns = ["routine did", "routine did", "rid", "rid号"]
        return self._find_column_by_patterns(rows, patterns, max_search_rows)

    def _find_dtc_column(self, rows: list[list], max_search_rows: int = 6) -> int | None:
        patterns = ["dtc number", "dtc编号", "dtc号", "fault code"]
        return self._find_column_by_patterns(rows, patterns, max_search_rows)

    def _find_column_by_patterns(
        self, rows: list[list], patterns: list[str], max_rows: int,
    ) -> int | None:
        for row in rows[:max_rows]:
            if not row:
                continue
            for col_idx, cell in enumerate(row):
                if not cell or not isinstance(cell, str):
                    continue
                cell_lower = cell.lower()
                if all(p in cell_lower for p in patterns[:1]):
                    # 至少匹配第一个关键 pattern
                    if any(p in cell_lower for p in patterns):
                        return col_idx
        # 退化：尝试第1列（DID/RID 通常在 col 1）
        return None

    def _count_unique_hex_in_column(
        self, rows: list[list], col: int, start_row: int = 3,
    ) -> int:
        """统计某列中唯一 hex 值的数量。"""
        seen = set()
        for row in rows[start_row:]:
            if col >= len(row):
                continue
            val = row[col]
            if not val or not isinstance(val, str):
                continue
            val = str(val).strip().replace("0x", "").replace("0X", "").replace(" ", "")
            if val and _HEX_PATTERN.match(val):
                seen.add(val.upper())
        return len(seen)

    def count_unique_dids(self) -> int | None:
        """从 DID sheet 统计唯一 DID 数量。"""
        did_sheets = self._find_sheets(self.DID_KEYWORDS)
        if not did_sheets:
            return None

        total = 0
        for name, data in did_sheets:
            rows = data.rows if hasattr(data, "rows") else []
            col = self._find_did_column(rows)
            if col is None:
                # 退化到第1列（通常是 DID hex 列）
                col = 1
            count = self._count_unique_hex_in_column(rows, col)
            total += count
            logger.debug(f"DID sheet \"{name}\": col={col}, count={count}")

        return total if total > 0 else None

    def count_subfunctions(self) -> int | None:
        """从服务 sheet 统计 App 域子功能数量。"""
        svc_sheets = self._find_sheets(self.SERVICE_KEYWORDS)
        if not svc_sheets:
            return None

        # TODO: 实现完整的服务 sheet 子功能计数
        # 这需要解析合并单元格 + service ID 列匹配
        # 暂时返回 None（不阻断验证流程）
        return None

    def count_unique_dtcs(self) -> int | None:
        """从 DTC sheet 统计唯一 DTC 数量。"""
        dtc_sheets = self._find_sheets(self.DTC_KEYWORDS)
        # 只取 "list" 类型的 sheet（排除 GroupOfDTC）
        dtc_sheets = [(n, d) for n, d in dtc_sheets if "list" in n.lower() or "04.2" in n.lower()]
        if not dtc_sheets:
            return None

        total = 0
        for name, data in dtc_sheets:
            rows = data.rows if hasattr(data, "rows") else []
            col = self._find_dtc_column(rows)
            if col is None:
                col = 1
            count = self._count_unique_hex_in_column(rows, col)
            total += count
            logger.debug(f"DTC sheet \"{name}\": col={col}, count={count}")

        return total if total > 0 else None

    def count_unique_rids(self) -> int | None:
        """从 Routine sheet 统计唯一 RID 数量。"""
        rid_sheets = self._find_sheets(self.ROUTINE_KEYWORDS)
        if not rid_sheets:
            return None

        total = 0
        for name, data in rid_sheets:
            rows = data.rows if hasattr(data, "rows") else []
            col = self._find_rid_column(rows)
            if col is None:
                col = 1
            count = self._count_unique_hex_in_column(rows, col)
            total += count
            logger.debug(f"RID sheet \"{name}\": col={col}, count={count}")

        return total if total > 0 else None


# ======================================================================
# 辅助函数（供 pipeline 使用）
# ======================================================================

def format_findings(report: ValidationReport) -> list[str]:
    """将 ValidationReport 转换为字符串警告列表（向后兼容）。"""
    lines = []
    for f in report.findings:
        prefix = {"error": "ERROR", "warning": "WARN", "info": "INFO"}[f.severity]
        fix_tag = " [AUTO-FIXED]" if f.auto_fixed else ""
        lines.append(f"[{prefix}][{f.rule_id}]{fix_tag} {f.message}")

    if report.findings:
        errors = sum(1 for f in report.findings if f.severity == "error" and not f.auto_fixed)
        warnings = sum(1 for f in report.findings if f.severity == "warning")
        lines.append(
            f"验证统计: {report.auto_fixes_applied} 项自动修复, "
            f"{errors} 项错误, {warnings} 项警告 "
            f"(Tier1={report.tier1_duration_ms:.0f}ms, Tier2={report.tier2_duration_ms:.0f}ms)"
        )
    return lines
