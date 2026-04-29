"""JSON 测试结果 → Excel 文件导出。

每个服务生成一个 Sheet，格式匹配 Het_UDS_TestSpecification 模板。
"""

from __future__ import annotations

import io
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


# 列宽配置（匹配模板）
COL_WIDTHS = {
    "A": 6,   # Sequence Number
    "B": 18,  # System Requirement ID
    "C": 18,  # Case ID
    "D": 55,  # Case Name
    "E": 8,   # Priority
    "F": 10,  # Author
    "G": 16,  # Design Method
    "H": 14,  # Precondition
    "I": 50,  # Test Procedure
    "J": 50,  # Expected Output
    "K": 12,  # Actual Output
    "L": 10,  # (empty)
    "M": 12,  # Defect ID
    "N": 10,
    "O": 10,
    "P": 10,
}

# 样式
THIN_BORDER = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)
HEADER_FILL = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
HEADER_FONT = Font(bold=True, color="FFFFFF", size=10)
SECTION_FILL = PatternFill(start_color="D9E2F3", end_color="D9E2F3", fill_type="solid")
SECTION_FONT = Font(bold=True, size=10)
NORMAL_FONT = Font(size=10)
WRAP_ALIGN = Alignment(wrap_text=True, vertical="top")


def export_to_excel(services_data: list[dict]) -> bytes:
    """将多个服务的测试用例导出为 Excel 字节流。

    Args:
        services_data: API 返回的 services 数组

    Returns:
        .xlsx 文件的字节内容
    """
    wb = Workbook()
    # 删除默认 Sheet
    wb.remove(wb.active)

    for svc in services_data:
        sheet_name = _safe_sheet_name(svc.get("sheet_name", "Sheet1"))
        ws = wb.create_sheet(title=sheet_name)

        # 设置列宽
        for col_letter, width in COL_WIDTHS.items():
            ws.column_dimensions[col_letter].width = width

        # 写表头
        _write_header(ws)

        # 写数据
        test_cases = svc.get("test_cases", [])
        row = 4  # 数据从第4行开始
        current_section = ""
        current_subsection = ""
        seq = 0

        for tc in test_cases:
            section = tc.get("section", "")
            subsection = tc.get("subsection", "")

            # 写 section header
            if section != current_section:
                current_section = section
                current_subsection = ""
                _write_section_row(ws, row, section)
                row += 1

            # 写 subsection header
            if subsection != current_subsection:
                current_subsection = subsection
                _write_section_row(ws, row, subsection)
                row += 1

            # 写 test case row
            seq += 1
            _write_test_case_row(ws, row, seq, tc)
            row += 1

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


def _write_header(ws):
    """写3行表头，匹配 Het_UDS_TestSpecification 模板。"""
    # Row 1: B1:C1 = "Test Level", D1:M1 = "SYS.5"
    ws["B1"] = "Test Level"
    ws["B1"].font = HEADER_FONT
    ws["B1"].fill = HEADER_FILL
    ws["B1"].alignment = Alignment(horizontal="center")
    ws["B1"].border = THIN_BORDER
    ws.merge_cells("B1:C1")

    ws["D1"] = "SYS.5"
    ws["D1"].font = HEADER_FONT
    ws["D1"].fill = HEADER_FILL
    ws["D1"].alignment = Alignment(horizontal="center")
    ws["D1"].border = THIN_BORDER
    ws.merge_cells("D1:M1")

    # Row 2: 列标题
    headers = [
        "Sequence Number",       # A
        "System Requirement ID", # B
        "Test Case",             # C
        "",                      # D (Name sub-header in row 3)
        "",                      # E (Priority sub-header in row 3)
        "",                      # F (Author sub-header in row 3)
        "Design Method",         # G
        "Precondition",          # H
        "Test Procedure",        # I
        "Expected Output",       # J
        "Actual Output",         # K
        "Judgement Result",      # L
        "Defect ID",             # M
        "", "", "",              # N-P
    ]
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=2, column=col, value=h)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.border = THIN_BORDER

    # Row 3: 子标题
    sub_headers = [
        "",       # A
        "",       # B
        "ID",     # C
        "Name",   # D
        "Priority",  # E
        "Author",    # F
    ] + [""] * 10  # G-P
    for col, h in enumerate(sub_headers, 1):
        cell = ws.cell(row=3, column=col, value=h)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.border = THIN_BORDER


def _write_section_row(ws, row, text):
    """写 section/subsection 标题行。"""
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=16)
    cell = ws.cell(row=row, column=1, value=text)
    cell.font = SECTION_FONT
    cell.fill = SECTION_FILL
    cell.alignment = Alignment(vertical="center")
    cell.border = THIN_BORDER


def _write_test_case_row(ws, row, seq, tc):
    """写一条测试用例。"""
    values = [
        seq,                                    # A: Sequence Number
        tc.get("system_requirement_id", ""),    # B: System Requirement ID
        tc.get("case_id", ""),                  # C: Case ID
        tc.get("case_name", ""),                # D: Case Name
        tc.get("priority", "High"),             # E: Priority
        tc.get("author", ""),                   # F: Author
        tc.get("design_method", ""),            # G: Design Method
        tc.get("precondition", ""),             # H: Precondition
        tc.get("test_procedure", ""),           # I: Test Procedure
        tc.get("expected_output", ""),          # J: Expected Output
        tc.get("actual_output", ""),            # K: Actual Output
        "",                                     # L
        tc.get("defect_id", ""),                # M: Defect ID
        "", "", "",                             # N-P
    ]

    for col, val in enumerate(values, 1):
        cell = ws.cell(row=row, column=col, value=val)
        cell.font = NORMAL_FONT
        cell.border = THIN_BORDER
        cell.alignment = WRAP_ALIGN


def _safe_sheet_name(name: str, max_len: int = 31) -> str:
    """确保 Sheet 名合法（最长31字符，不含特殊字符）。"""
    for ch in ("\\", "/", "*", "?", ":", "[", "]"):
        name = name.replace(ch, "_")
    return name[:max_len]
