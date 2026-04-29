"""SheetData → LLM 可读文本转换器，带智能 Sheet 过滤。"""

from __future__ import annotations

import re
from typing import Any

from .reader import SheetData

# 数据结束哨兵模式（大小写不敏感）
_SENTINEL_RE = re.compile(r"#endofdata", re.IGNORECASE)


class SheetTextConverter:
    """将 SheetData 转为 LLM 可读文本，带智能 Sheet 过滤。"""

    DEFAULT_RELEVANT_KEYWORDS = [
        "basic", "diagnostic", "service", "did", "dtc", "routine",
        "session", "nrc", "timing", "general", "0x",
        "诊断", "服务", "基本",
    ]

    DEFAULT_EXCLUDE_KEYWORDS = [
        "history", "change", "revision", "instruction", "formula",
        "predefined", "template", "legend", "kangatang",
        "document", "cover",
    ]

    def __init__(
        self,
        relevant_keywords: list[str] | None = None,
        exclude_keywords: list[str] | None = None,
        max_rows: int = 200,
    ):
        self._relevant = relevant_keywords or self.DEFAULT_RELEVANT_KEYWORDS
        self._exclude = exclude_keywords or self.DEFAULT_EXCLUDE_KEYWORDS
        self._max_rows = max_rows

    def convert_workbook(
        self,
        sheets: dict[str, SheetData],
        filter_sheets: bool = True,
    ) -> str:
        """转换整个工作簿为文本。filter_sheets=True 时自动过滤无关 Sheet。"""
        if filter_sheets:
            names = self.filter_relevant_sheets(list(sheets.keys()))
        else:
            names = list(sheets.keys())

        parts: list[str] = []
        for name in names:
            if name in sheets:
                text = self.convert_sheet(sheets[name])
                if text.strip():
                    parts.append(text)

        return "\n\n".join(parts)

    def convert_sheet(self, sheet_data: SheetData) -> str:
        """转换单个 Sheet 为文本。"""
        lines: list[str] = []
        lines.append(
            f"=== Sheet: {sheet_data.sheet_name} "
            f"({sheet_data.max_row} rows x {sheet_data.max_col} cols) ==="
        )

        for i, row in enumerate(sheet_data.rows):
            if i >= self._max_rows:
                lines.append(f"... (truncated at {self._max_rows} rows)")
                break

            # 检测哨兵（第一列）
            first_val = str(row[0]).strip() if row and row[0] is not None else ""
            if _SENTINEL_RE.search(first_val):
                break

            # 跳过全空行
            vals = [_format_cell(v) for v in row]
            if all(v == "" for v in vals):
                continue

            lines.append(f"Row {i + 1}: {' | '.join(vals)}")

        return "\n".join(lines)

    def filter_relevant_sheets(self, sheet_names: list[str]) -> list[str]:
        """智能过滤：保留 relevant Sheet，排除 exclude 的，其余保留。"""
        result: list[str] = []
        for name in sheet_names:
            lower = name.lower()
            # 先检查排除
            if any(kw.lower() in lower for kw in self._exclude):
                continue
            # 检查是否 relevant
            if any(kw.lower() in lower for kw in self._relevant):
                result.append(name)
            else:
                # 既不 relevant 也不 exclude → 保留（宁可多传也不漏）
                result.append(name)
        return result


def _format_cell(value: Any) -> str:
    """格式化单元格值为文本。"""
    if value is None:
        return ""
    s = str(value).strip()
    if s.lower() in ("none", "nan", "null"):
        return ""
    return s
