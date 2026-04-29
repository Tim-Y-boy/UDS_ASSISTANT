"""UDS 测试用例生成管道入口。"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# 将 src/ 加入 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from src.uds_agent.generate_pipeline import UDSGeneratePipeline


def main():
    parser = argparse.ArgumentParser(description="UDS 测试用例生成管道")
    parser.add_argument("--input", required=True, help="ECU 诊断参数 Excel 文件路径")
    parser.add_argument("--service", required=True, help="目标服务 ID，如 0x10")
    parser.add_argument("--config", default="config.yaml", help="配置文件路径（默认 config.yaml）")
    parser.add_argument("--domain", default="App", choices=["App", "BootLoader"], help="软件域")
    parser.add_argument("--output", default=None, help="输出 JSON 文件路径（默认打印到终端）")
    parser.add_argument("--verbose", action="store_true", help="显示详细日志（包括故障转移过程）")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")

    pipeline = UDSGeneratePipeline(config_path=args.config)

    result = pipeline.generate(
        excel_path=args.input,
        service_id=args.service,
        domain=args.domain,
    )

    text = json.dumps(result.model_dump(), ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"结果已写入: {args.output}")
    else:
        print(text)

    if result.meta.get("error"):
        print(f"\n错误: {result.meta['error']}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
