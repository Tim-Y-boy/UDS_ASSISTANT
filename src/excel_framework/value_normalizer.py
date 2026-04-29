"""通用值标准化工具。"""

from __future__ import annotations

import re
from typing import Any


class ValueNormalizer:
    """对 LLM 提取后的值做后处理标准化。"""

    _TRUE_VALUES = {"x", "X", "y", "Y", "yes", "Yes", "YES", "M", "m", "true", "True"}
    _FALSE_VALUES = {"n", "N", "no", "No", "NO", "-", "/", "\\", "false", "False", ""}

    @staticmethod
    def to_bool(value: Any) -> bool:
        s = str(value).strip()
        if s in ValueNormalizer._TRUE_VALUES:
            return True
        if s in ValueNormalizer._FALSE_VALUES:
            return False
        return bool(s)

    @staticmethod
    def to_hex(value: Any, strip_prefix: bool = True) -> str:
        s = str(value).strip()
        m = re.search(r"0x([0-9a-fA-F]+)", s, re.IGNORECASE)
        if m:
            return m.group(1) if strip_prefix else f"0x{m.group(1)}"
        m = re.search(r"([0-9a-fA-F]{2,})", s)
        if m:
            return m.group(1) if strip_prefix else f"0x{m.group(1)}"
        return s

    @staticmethod
    def to_int_ms(value: Any) -> int:
        s = str(value).strip()
        m = re.search(r"[\d.]+", s)
        if not m:
            return 0
        num = float(m.group())
        if "s" in s.lower() and "ms" not in s.lower():
            num *= 1000
        return int(num)

    @staticmethod
    def normalize_nrc(value: str) -> list[str]:
        """从两种 NRC 格式提取纯 NRC 代码列表。

        格式A: "12,13,22,7E"
        格式B: "7F>13>12>13>7E>24"
        """
        if not value:
            return []
        # 统一用 > 或 , 分割
        codes = re.split(r"[>,\s]+", value.strip())
        # 过滤掉已知的非 NRC 标记（如 7F 是负响应 SID 前缀）
        skip = {"7F", "7f", "7f"}
        result = []
        seen = set()
        for c in codes:
            c = c.strip().upper()
            if not c or c in skip or c in seen:
                continue
            # 合法的 NRC 是 2 位十六进制
            if re.fullmatch(r"[0-9A-F]{2}", c):
                seen.add(c)
                result.append(c)
        return result
