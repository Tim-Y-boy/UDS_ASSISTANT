"""本地 MCP 入口 — 直接引用项目源码，无重复代码。"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.excel_framework import ExcelReader, SheetTextConverter
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "excel-parser",
    instructions=(
        "通用 Excel 文件解析工具，支持 .xlsx 和 .xls 格式。"
        "使用 list_sheets 探索文件结构，再用 read_excel 或 read_single_sheet 读取内容。"
    ),
)


@mcp.tool()
def list_sheets(file_path: str) -> str:
    """列出 Excel 文件的所有 Sheet 名称及基本信息（行数、列数、合并单元格数）。"""
    try:
        reader = ExcelReader(file_path)
        sheets = reader.read_all_sheets()
        return json.dumps([
            {"name": n, "rows": s.max_row, "cols": s.max_col, "merged_cells": len(s.merged_ranges)}
            for n, s in sheets.items()
        ], ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@mcp.tool()
def read_excel(
    file_path: str,
    filter_sheets: bool = True,
    relevant_keywords: list[str] | None = None,
    exclude_keywords: list[str] | None = None,
    max_rows: int = 200,
) -> str:
    """读取 Excel 文件并转换为文本。自动过滤无关 Sheet，解析合并单元格。"""
    try:
        reader = ExcelReader(file_path, max_rows_per_sheet=max_rows)
        sheets = reader.read_all_sheets()
        converter = SheetTextConverter(
            relevant_keywords=relevant_keywords,
            exclude_keywords=exclude_keywords,
            max_rows=max_rows,
        )
        text = converter.convert_workbook(sheets, filter_sheets=filter_sheets)
        filtered = converter.filter_relevant_sheets(list(sheets.keys())) if filter_sheets else list(sheets.keys())
        return json.dumps({
            "text": text,
            "stats": {
                "total_sheets": len(sheets),
                "filtered_sheets": len(filtered),
                "text_length": len(text),
                "sheet_names": filtered,
            },
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@mcp.tool()
def read_single_sheet(file_path: str, sheet_name: str, max_rows: int = 200) -> str:
    """读取 Excel 文件中指定 Sheet 的内容。"""
    try:
        reader = ExcelReader(file_path, max_rows_per_sheet=max_rows)
        sd = reader.read_sheet(sheet_name)
        converter = SheetTextConverter(max_rows=max_rows)
        return json.dumps({
            "sheet": sheet_name, "rows": sd.max_row, "cols": sd.max_col,
            "text": converter.convert_sheet(sd),
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run(transport="stdio")
