"""UDS 诊断参数提取的 Pydantic 模型定义。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class BasicInfo(BaseModel):
    ecu_name: str = ""
    protocol: str = ""
    canid_req: str = ""
    canid_resp: str = ""
    canid_func: str = ""
    p2_ms: int = 0
    p2star_ms: int = 0
    s3_ms: int = 0
    p2_hex: str = ""           # e.g. "0032"
    p2star_hex: str = ""       # e.g. "00C8"
    nrc_priority_chain: str = ""  # e.g. "13>12>22>7E"
    reset_time_support: bool = False
    reset_time_byte_length: int = 0


class SubfunctionEntry(BaseModel):
    subfunction: str = ""
    subfunction_name: str = ""
    support: bool = True
    sprmib: bool = False
    physical_req: bool = False
    functional_req: bool = False
    session_default: bool = False
    session_extended: bool = False
    session_programming: bool = False
    access_level: str = ""
    nrc_codes: list[str] = Field(default_factory=list)
    domain: str = ""           # "App" or "Boot"


class ServiceMatrix(BaseModel):
    service_id: str = ""
    service_name: str = ""
    subfunctions: list[SubfunctionEntry] = Field(default_factory=list)


class DIDEntry(BaseModel):
    did_number: str = ""
    did_name: str = ""
    byte_length: int = 0
    read_support: bool = False
    write_support: bool = False
    read_access_level: str = ""
    write_access_level: str = ""
    session: str = ""


class DTCEntry(BaseModel):
    dtc_number: str = ""
    dtc_name: str = ""
    status_mask: str = ""
    trigger_conditions: str = ""
    trigger_method: str = ""        # e.g. "Stop MsgCycle[<FaultMsgId>]"
    trigger_delay_ms: int = 0       # e.g. 3000
    recovery_method: str = ""       # e.g. "Send MsgCycle[<FaultMsgId>]"
    recovery_delay_ms: int = 0      # e.g. 3000


class RIDEntry(BaseModel):
    rid_number: str = ""
    rid_name: str = ""
    subfunction: str = ""
    access_level: str = ""
    request_params: str = ""
    response_params: str = ""


class SecurityAccessEntry(BaseModel):
    level: str = ""          # "L2"
    seed_sub: str = ""       # "03"
    key_sub: str = ""        # "04"
    domain: str = ""         # "App"


class ResetSubfunctionEntry(BaseModel):
    subfunction: str = ""    # "01"
    name: str = ""           # "Hard Reset"
    support: bool = False
    domain: str = ""         # "App"


class FullExtractionResult(BaseModel):
    basic_info: BasicInfo = Field(default_factory=BasicInfo)
    service_matrix: ServiceMatrix = Field(default_factory=ServiceMatrix)
    boot_matrix: ServiceMatrix | None = None
    did_list: list[DIDEntry] = Field(default_factory=list)
    dtc_list: list[DTCEntry] = Field(default_factory=list)
    routine_list: list[RIDEntry] = Field(default_factory=list)
    security_list: list[SecurityAccessEntry] = Field(default_factory=list)
    reset_subfunctions: list[ResetSubfunctionEntry] = Field(default_factory=list)
    k_column_rules: list[str] = Field(default_factory=list)


class ValidationFinding(BaseModel):
    """单条验证发现。"""
    rule_id: str              # "T1_P2_HEX", "T2_DID_COUNT"
    severity: str             # "error" | "warning" | "info"
    message: str              # 人类可读描述
    field_path: str           # "basic_info.p2_hex"
    auto_fixed: bool = False
    old_value: str = ""
    new_value: str = ""


class ValidationReport(BaseModel):
    """一次提取的完整验证报告。"""
    findings: list[ValidationFinding] = Field(default_factory=list)
    auto_fixes_applied: int = 0
    tier1_duration_ms: float = 0.0
    tier2_duration_ms: float = 0.0
