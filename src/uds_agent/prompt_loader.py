"""可配置的提示词加载 + 参数格式化。"""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from .schemas import FullExtractionResult


def load_config(config_path: str = "config.yaml") -> dict:
    path = os.path.abspath(config_path)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def load_service_prompt(service_id: str, config_path: str = "config.yaml") -> str:
    """从 config.yaml 的 service_prompts 映射加载提示词文件。"""
    cfg = load_config(config_path)
    prompts_map: dict = cfg.get("service_prompts", {})

    # 标准化 service_id
    sid = service_id.lower()
    if not sid.startswith("0x"):
        sid = "0x" + sid

    prompt_file = prompts_map.get(sid)
    if not prompt_file:
        raise FileNotFoundError(
            f"服务 {sid} 未配置提示词。请在 config.yaml 的 service_prompts 中添加映射。\n"
            f"已配置的服务: {', '.join(prompts_map.keys())}"
        )

    path = Path(prompt_file)
    if not path.is_absolute():
        base = Path(config_path).parent
        path = base / path

    if not path.exists():
        raise FileNotFoundError(f"提示词文件不存在: {path}")

    return path.read_text(encoding="utf-8")


def load_generation_config(config_path: str = "config.yaml") -> dict:
    """读取 generation 配置段。"""
    cfg = load_config(config_path)
    return cfg.get("generation", {})


def _format_subfunction_table(subfunctions: list, title: str) -> list[str]:
    """格式化子功能表格。"""
    parts: list[str] = []
    parts.append(f"\n## {title}\n")
    parts.append("| 子功能 | 名称 | Support | SPRMIB | Physical | Functional | Default | Extended | Programming | Access Level | NRC | Domain |")
    parts.append("|--------|------|---------|--------|----------|------------|---------|----------|-------------|-------------|-----|--------|")
    for sf in subfunctions:
        parts.append(
            f"| {sf.subfunction} | {sf.subfunction_name} | "
            f"{'Y' if sf.support else 'N'} | {'Y' if sf.sprmib else 'N'} | "
            f"{'Y' if sf.physical_req else 'N'} | {'Y' if sf.functional_req else 'N'} | "
            f"{'Y' if sf.session_default else 'N'} | {'Y' if sf.session_extended else 'N'} | "
            f"{'Y' if sf.session_programming else 'N'} | {sf.access_level} | "
            f"{', '.join(sf.nrc_codes)} | {sf.domain} |"
        )
    return parts


def build_generation_user_message(
    extraction_result: FullExtractionResult,
    service_id: str,
) -> str:
    """将提取的参数格式化为 LLM 可读的 user message。"""
    parts: list[str] = []

    sid = service_id.lower()
    if not sid.startswith("0x"):
        sid = "0x" + sid

    bi = extraction_result.basic_info

    # --- ECU 基本参数（含 P2/P2* hex 编码） ---
    parts.append("## ECU 基本参数\n")
    parts.append(f"- ECU名称: {bi.ecu_name}")
    parts.append(f"- 协议: {bi.protocol}")
    parts.append(f"- 请求 CAN ID: {bi.canid_req}")
    parts.append(f"- 响应 CAN ID: {bi.canid_resp}")
    parts.append(f"- 功能寻址 CAN ID: {bi.canid_func}")
    parts.append(f"- P2: {bi.p2_ms}ms → hex: {bi.p2_hex or '(未提取)'}")
    parts.append(f"- P2*: {bi.p2star_ms}ms → hex: {bi.p2star_hex or '(未提取)'}")
    parts.append(f"- S3: {bi.s3_ms}ms")
    parts.append(f"- P2/P2* hex 编码规则: P2 = P2_ms 直接转4位大写hex; P2* = P2star_ms ÷ 10 后转4位大写hex")
    if bi.reset_time_support:
        parts.append(f"- Reset Time: 支持 (字节长度: {bi.reset_time_byte_length})")
    else:
        parts.append("- Reset Time: 不支持")

    # --- NRC 优先级链 ---
    if bi.nrc_priority_chain:
        parts.append(f"- NRC 优先级链: {bi.nrc_priority_chain}")

    # --- App 域服务矩阵 ---
    sm = extraction_result.service_matrix
    if sm.subfunctions:
        parts.extend(_format_subfunction_table(
            sm.subfunctions,
            f"服务 {sid} ({sm.service_name}) App 域参数矩阵",
        ))

    # --- Boot 域矩阵 ---
    bm = extraction_result.boot_matrix
    if bm and bm.subfunctions:
        parts.extend(_format_subfunction_table(
            bm.subfunctions,
            f"服务 {sid} ({bm.service_name or sm.service_name}) Boot 域参数矩阵",
        ))

    # --- 安全访问映射 ---
    if extraction_result.security_list:
        parts.append("\n## 安全访问映射 (0x27)\n")
        parts.append("| Level | Seed Sub | Key Sub | Domain |")
        parts.append("|-------|----------|---------|--------|")
        for s in extraction_result.security_list:
            parts.append(f"| {s.level} | {s.seed_sub} | {s.key_sub} | {s.domain} |")
        parts.append("- 生成安全访问步骤时使用对应的 Seed/Key 子功能对")

    # --- 0x11 ECU Reset 子功能列表 ---
    if extraction_result.reset_subfunctions:
        parts.append("\n## 0x11 ECUReset 子功能列表\n")
        parts.append("| Subfunction | 名称 | Support | Domain |")
        parts.append("|-------------|------|---------|--------|")
        for r in extraction_result.reset_subfunctions:
            parts.append(f"| {r.subfunction} | {r.name} | {'Y' if r.support else 'N'} | {r.domain} |")
        parts.append("- 生成 ECU Reset 相关用例时使用此列表中的子功能")

    # --- DID 列表 ---
    if extraction_result.did_list:
        parts.append("\n## DID 列表\n")
        parts.append("| DID | 名称 | 字节长度 | Read | Write | Read Level | Write Level | Session |")
        parts.append("|-----|------|---------|------|-------|-----------|------------|---------|")
        for d in extraction_result.did_list:
            parts.append(
                f"| {d.did_number} | {d.did_name} | {d.byte_length} | "
                f"{'Y' if d.read_support else 'N'} | {'Y' if d.write_support else 'N'} | "
                f"{d.read_access_level} | {d.write_access_level} | {d.session} |"
            )

    # --- DTC 列表 ---
    if extraction_result.dtc_list:
        parts.append("\n## DTC 列表\n")
        parts.append("| DTC | 名称 | Status Mask | 触发条件 |")
        parts.append("|-----|------|-------------|----------|")
        for d in extraction_result.dtc_list:
            parts.append(f"| {d.dtc_number} | {d.dtc_name} | {d.status_mask} | {d.trigger_conditions} |")

    # --- RID 列表 ---
    if extraction_result.routine_list:
        parts.append("\n## RID 列表\n")
        parts.append("| RID | 名称 | Subfunction | Access Level |")
        parts.append("|-----|------|-------------|-------------|")
        for r in extraction_result.routine_list:
            parts.append(f"| {r.rid_number} | {r.rid_name} | {r.subfunction} | {r.access_level} |")

    # --- 生成指令 ---
    has_boot = bm and bm.subfunctions
    domain_hint = "（包括 App 域和 Boot 域）" if has_boot else ""

    parts.append(f"\n请根据以上参数和系统提示词中的规则，生成服务 {sid} 的完整测试用例{domain_hint}。")

    # --- 动态输出格式模板 ---
    p2_hex_str = bi.p2_hex or "XXXX"
    p2star_hex_str = bi.p2star_hex or "XXXX"
    p2_ms_str = str(bi.p2_ms) if bi.p2_ms > 0 else "XX"
    p2_hex_display = f"{p2_hex_str[:2]} {p2_hex_str[2:]}" if len(p2_hex_str) == 4 else f"{p2_hex_str}"
    p2star_hex_display = f"{p2star_hex_str[:2]} {p2star_hex_str[2:]}" if len(p2star_hex_str) == 4 else f"{p2star_hex_str}"
    resp_prefix = f"{int(sid, 16) + 0x40:02X}"

    parts.append(f"""
---
# 输出格式（最高优先级，必须严格遵守）

你的输出必须严格按以下格式生成每条测试用例。禁止使用其他格式。

每个测试类别用三级标题，每条用例用四级标题：

### 1.1 测试类别名称
#### 1.1.1 用例名称写在这里
- **Case ID**: Diag_{sid}_Phy_001
- **Steps**:
  1. Send DiagBy[Physical]Data[10 01];
  2. Send DiagBy[Physical]Data[10 03];
- **Expected Output**:
  1. Check DiagData[{resp_prefix} 01 {p2_hex_display} {p2star_hex_display}]Within[{p2_ms_str}]ms;
  2. Check DiagData[{resp_prefix} 03 {p2_hex_display} {p2star_hex_display}]Within[{p2_ms_str}]ms;

#### 1.1.2 下一条用例名称
- **Case ID**: Diag_{sid}_Phy_002
- **Steps**:
  1. Send DiagBy[Physical]Data[10 01];
- **Expected Output**:
  1. Check DiagData[{resp_prefix} 01 {p2_hex_display} {p2star_hex_display}]Within[{p2_ms_str}]ms;

### 1.2 下一个测试类别
...（以此类推）

格式硬性要求：
1. 每个测试类别用 `### N.M 类别名`，从 1.1 开始编号
2. 每条用例用 `#### N.M.N 用例名称`，编号连续递增
3. Case ID 严格格式：`Diag_{sid}_Phy_NNN`（物理寻址）或 `Diag_{sid}_Fun_NNN`（功能寻址），NNN 为三位流水号
   - 物理寻址从 **001** 开始编号
   - 功能寻址从 **001** 开始编号
4. 每条用例必须且只能包含三个字段，顺序固定：
   - `- **Case ID**: <值>`（一行，无换行）
   - `- **Steps**:` 后跟编号步骤列表
   - `- **Expected Output**:` 后跟编号预期结果列表
5. 步骤编号格式：`  1. `（两个空格缩进 + 数字 + 点 + 空格）
6. Steps 中只写动作（Send / Delay / Set Voltage 等），不写 Check
7. Expected Output 中只写检查（Check DiagData / Check No_Response 等）
8. 禁止在 Steps 中内嵌 Check 或 *Check* 注释
9. 禁止添加 Objective、Precondition、Postcondition、Notes 等额外字段
10. 完成所有用例后，在末尾输出 `## 用例统计汇总` 表格
11. 正响应报文中的 P2 hex 必须是 `{p2_hex_display}`（{bi.p2_ms}ms），P2* hex 必须是 `{p2star_hex_display}`（{bi.p2star_ms}ms÷10），禁止使用其他值
""")

    return "\n".join(parts)


# 服务名称映射（用于生成 sheet_name）
SERVICE_NAMES: dict[str, str] = {
    "0x10": "DiagnosticSessionControl",
    "0x11": "ECUReset",
    "0x14": "ClearDiagnosticInformation",
    "0x19": "ReadDTCInformation",
    "0x22": "ReadDataByIdentifier",
    "0x27": "SecurityAccess",
    "0x28": "CommunicationControl",
    "0x2e": "WriteDataByIdentifier",
    "0x2E": "WriteDataByIdentifier",
    "0x31": "RoutineControl",
    "0x3e": "TesterPresent",
    "0x3E": "TesterPresent",
    "0x85": "ControlDTCSettings",
}


def build_sheet_name(service_id: str) -> str:
    sid = service_id.lower()
    if not sid.startswith("0x"):
        sid = "0x" + sid
    name = SERVICE_NAMES.get(sid, f"Service{sid}")
    return f"{name}_{sid}"
