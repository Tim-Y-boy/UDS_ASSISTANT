"""Excel 读取 + 文本转换管道（纯代码，无 LLM）。"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ..excel_framework import ExcelReader, SheetTextConverter

logger = logging.getLogger("pipeline")

# Excel 文本输出目录
_DUMP_DIR = Path(__file__).parent.parent.parent / "logs" / "excel_text"


def _dump_excel_text(excel_path: str, service_id: str, text: str) -> None:
    if not text:
        return
    _DUMP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = Path(excel_path).stem
    out_path = _DUMP_DIR / f"{timestamp}_{filename}_{service_id}.txt"
    out_path.write_text(text, encoding="utf-8")
    logger.info(f"Excel 文本已写入: {out_path}")


@dataclass
class ExtractionOutput:
    """Excel 读取管道的输出。"""

    excel_text: str = ""
    elapsed_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)
    excel_text_length: int = 0
    sheets_filtered: list[str] = field(default_factory=list)


class UDSExtractionPipeline:
    """Excel → 文本 的纯代码管道。"""

    def __init__(self, config_path: str = "config.yaml", **kwargs):
        self._config_path = config_path

    def extract(
        self,
        excel_path: str,
        service_id: str = "",
        software_domain: str = "App",
        original_filename: str = "",
    ) -> ExtractionOutput:
        """读取 Excel 并转换为文本。"""
        start = time.time()

        # 1. 读取 Excel
        try:
            reader = ExcelReader(excel_path)
            sheets = reader.read_all_sheets()
        except FileNotFoundError as e:
            return ExtractionOutput(
                errors=[f"ERR_FILE_INVALID: {e}"],
                elapsed_seconds=time.time() - start,
            )
        except Exception as e:
            return ExtractionOutput(
                errors=[f"ERR_FILE_INVALID: {e}"],
                elapsed_seconds=time.time() - start,
            )

        # 2. 转换为文本（带智能过滤）
        converter = SheetTextConverter()
        all_names = list(sheets.keys())
        filtered_names = converter.filter_relevant_sheets(all_names)
        excel_text = converter.convert_workbook(sheets, filter_sheets=True)

        output = ExtractionOutput(
            excel_text=excel_text,
            elapsed_seconds=time.time() - start,
            excel_text_length=len(excel_text),
            sheets_filtered=filtered_names,
        )

        # 将解析出的文本写入文件
        _dump_excel_text(original_filename or excel_path, service_id, excel_text)

        return output
