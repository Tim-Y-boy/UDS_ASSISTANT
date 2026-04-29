"""测试用例输出的 Pydantic 模型定义，匹配 Excel 模板格式。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TestCaseRow(BaseModel):
    """单条测试用例，对应 Excel 中一行数据。"""

    section: str = ""
    subsection: str = ""
    sequence_number: int = 0
    system_requirement_id: str = ""
    case_id: str = ""
    case_name: str = ""
    priority: str = "High"
    author: str = "Percy"
    design_method: str = "Based on analysis of requirements"
    precondition: str = "1.Power On;"
    test_procedure: str = ""
    expected_output: str = ""
    actual_output: str = ""
    defect_id: str = ""


class SectionSummary(BaseModel):
    """用例统计汇总中的单个分类。"""

    section_name: str = ""
    physical_count: int = 0
    functional_count: int = 0
    total_count: int = 0


class ServiceTestResult(BaseModel):
    """单个服务的完整测试结果，对应 Excel 中一个 Sheet。"""

    service_id: str = ""
    service_name: str = ""
    sheet_name: str = ""
    total_count: int = 0
    test_cases: list[TestCaseRow] = Field(default_factory=list)
    sections_summary: list[SectionSummary] = Field(default_factory=list)
    meta: dict = Field(default_factory=dict)


class GenerateResponse(BaseModel):
    """API 响应：多服务合并结果。"""

    ecu_info: dict = Field(default_factory=dict)
    services: list[ServiceTestResult] = Field(default_factory=list)
    meta: dict = Field(default_factory=dict)
