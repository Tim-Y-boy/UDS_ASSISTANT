"""UDS 诊断参数提取管道入口。"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# 将 src/ 加入 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from src.uds_agent.pipeline import UDSExtractionPipeline


def main():
    parser = argparse.ArgumentParser(description="UDS 诊断参数提取管道")
    parser.add_argument("--input", required=True, help="ECU 诊断参数 Excel 文件路径")
    parser.add_argument("--service", required=True, help="目标服务 ID，如 0x10")
    parser.add_argument("--config", default="config.yaml", help="配置文件路径（默认 config.yaml）")
    parser.add_argument("--domain", default="App", choices=["App", "BootLoader"], help="软件域")
    parser.add_argument("--output", default=None, help="输出 JSON 文件路径（默认打印到终端）")
    parser.add_argument("--verbose", action="store_true", help="显示详细日志（包括故障转移过程）")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")

    pipeline = UDSExtractionPipeline(config_path=args.config)

    output = pipeline.extract(
        excel_path=args.input,
        service_id=args.service,
        software_domain=args.domain,
    )

    result_dict = {
        "basic_info": output.result.basic_info.model_dump(),
        "service_matrix": output.result.service_matrix.model_dump(),
        "did_list": [d.model_dump() for d in output.result.did_list],
        "dtc_list": [d.model_dump() for d in output.result.dtc_list],
        "routine_list": [r.model_dump() for r in output.result.routine_list],
        "k_column_rules": output.result.k_column_rules,
        "_meta": {
            "provider": output.provider_used,
            "model": output.model_used,
            "elapsed_seconds": round(output.elapsed_seconds, 2),
            "excel_text_length": output.excel_text_length,
            "sheets_filtered": output.sheets_filtered,
            "llm_usage": output.llm_usage,
            "errors": output.errors,
            "warnings": output.validation_warnings,
        },
    }

    text = json.dumps(result_dict, ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"结果已写入: {args.output}")
    else:
        print(text)

    if output.errors:
        print(f"\n错误: {output.errors}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
