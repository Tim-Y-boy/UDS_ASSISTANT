"""可配置的提示词加载 + 参数格式化。"""

from __future__ import annotations

import os
from pathlib import Path

import yaml


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


def build_generation_user_message(
    excel_text: str,
    service_id: str,
) -> str:
    """将 Excel 原始文本格式化为 LLM 可读的 user message。"""
    sid = service_id.lower()
    if not sid.startswith("0x"):
        sid = "0x" + sid

    parts: list[str] = []

    parts.append(f"## 提取目标\n")
    parts.append(f"- 服务 ID: {sid}")
    parts.append(f"- 需要提取: 基本参数（含P2/P2* hex编码、NRC优先级链、reset_time）+ App域和Boot域服务支持矩阵 + 0x27安全访问映射 + 0x11子功能列表")

    sid_num = sid.replace("0x", "")
    if sid_num in ("22", "2e"):
        parts.append(" + DID 列表")
    elif sid_num in ("14", "19"):
        parts.append(" + DTC 列表")
    elif sid_num == "31":
        parts.append(" + RID 列表")

    parts.append(f"\n请根据以上参数和系统提示词中的规则，生成服务 {sid} 的完整测试用例。")

    parts.append(f"\n## Excel 原始文本\n\n{excel_text}")

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
