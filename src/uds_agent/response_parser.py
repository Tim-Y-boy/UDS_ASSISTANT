"""LLM JSON 响应解析器，处理各种输出变体。"""

from __future__ import annotations

import json
import re

from .schemas import FullExtractionResult


def parse_json_response(text: str) -> dict:
    """从 LLM 响应文本中提取 JSON。

    处理以下变体：
    - 直接 JSON
    - ```json ... ``` 包裹
    - 前后有额外文字
    """
    text = text.strip()

    # 尝试1：直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试2：提取 markdown 代码块
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 尝试3：找第一个 { ... } 块
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    start = -1

    raise ValueError("无法从 LLM 响应中提取有效 JSON")


def validate_extraction(data: dict) -> tuple[FullExtractionResult, list[str]]:
    """用 Pydantic 校验提取结果，返回 (结果, 警告列表)。"""
    warnings: list[str] = []

    try:
        result = FullExtractionResult.model_validate(data)
    except Exception as e:
        # 宽松模式：尽量用默认值填充
        result = FullExtractionResult()
        warnings.append(f"Pydantic 校验失败，使用默认值: {e}")

    # 检查关键字段
    if not result.basic_info.ecu_name:
        warnings.append("basic_info.ecu_name 为空，可能未找到 ECU 基本信息表")
    if not result.service_matrix.subfunctions:
        warnings.append("service_matrix.subfunctions 为空，可能未找到目标服务")
    if not result.basic_info.p2_hex and result.basic_info.p2_ms > 0:
        warnings.append("basic_info.p2_hex 为空，LLM 未预计算 P2 hex 编码")
    if not result.basic_info.p2star_hex and result.basic_info.p2star_ms > 0:
        warnings.append("basic_info.p2star_hex 为空，LLM 未预计算 P2* hex 编码")

    return result, warnings
