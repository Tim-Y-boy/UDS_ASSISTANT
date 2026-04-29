"""构建 LLM 参数提取提示词。"""

from __future__ import annotations

from pathlib import Path


def load_extract_prompt(prompts_dir: str = "prompts") -> str:
    """加载提取提示词模板。"""
    path = Path(prompts_dir) / "extract_prompt.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    raise FileNotFoundError(f"提取提示词文件不存在: {path}")


def build_extraction_messages(
    excel_text: str,
    service_id: str,
    software_domain: str = "App",
    prompts_dir: str = "prompts",
) -> tuple[str, str]:
    """构建 (system_prompt, user_message)。

    Returns:
        (system_prompt, user_message) 用于 LLM 调用。
    """
    system_prompt = load_extract_prompt(prompts_dir)

    extra_hints = _build_extra_hints(service_id)

    user_message = (
        f"## 提取目标\n\n"
        f"- 服务 ID: {service_id}\n"
        f"- 软件域: {software_domain}\n"
        f"- 需要提取: {extra_hints}\n\n"
        f"## Excel 原始文本\n\n{excel_text}"
    )

    return system_prompt, user_message


def _build_extra_hints(service_id: str) -> str:
    """根据服务 ID 构建额外提取提示。"""
    sid = service_id.lower().replace("0x", "")
    hints = "基本参数（含P2/P2* hex编码、NRC优先级链、reset_time）+ App域和Boot域服务支持矩阵 + 0x27安全访问映射 + 0x11子功能列表"

    if sid in ("22", "2e"):
        hints += " + DID 列表（从含 DID 的 Sheet 中提取）"
    elif sid in ("14", "19"):
        hints += " + DTC 列表（从含 DTC 的 Sheet 中提取）"
    elif sid == "31":
        hints += " + RID 列表（从含 Routine 的 Sheet 中提取）"

    return hints
