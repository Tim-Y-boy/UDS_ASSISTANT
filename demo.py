"""UDS ASSISTANT 演示脚本 — 展示模块1（Excel解析）和完整生成流程。

运行方式：
  python demo.py                          # 仅模块1（Excel 解析展示）
  python demo.py --generate              # 模块1 + LLM 生成测试用例（需要 config.yaml 中有 API Key）
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.excel_framework import ExcelReader, SheetTextConverter


def separator(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def demo_module1(excel_path: str):
    """演示模块1：Excel 读取 → 文本转换。"""

    # ── 步骤1：读取 Excel ──
    separator("步骤1: ExcelReader — 读取 Excel 文件")
    print(f"  文件: {excel_path}")
    reader = ExcelReader(excel_path)
    sheets = reader.read_all_sheets()
    print(f"  共读取 {len(sheets)} 个 Sheet\n")

    for name, sd in sheets.items():
        print(f"  [{name}]  {sd.max_row} 行 x {sd.max_col} 列  (合并单元格: {len(sd.merged_ranges)})")

    # ── 步骤2：智能过滤 ──
    separator("步骤2: SheetTextConverter — 智能过滤")
    converter = SheetTextConverter()
    all_names = list(sheets.keys())
    filtered = converter.filter_relevant_sheets(all_names)
    excluded = [n for n in all_names if n not in filtered]

    print(f"  过滤前: {len(all_names)} 个 Sheet")
    print(f"  过滤后: {len(filtered)} 个 Sheet  (排除了 {len(excluded)} 个)\n")

    print(f"  保留:")
    for n in filtered:
        print(f"    + {n}")
    print(f"\n  排除:")
    for n in excluded:
        print(f"    - {n}")

    # ── 步骤3：文本转换 ──
    separator("步骤3: 转换为文本")
    text = converter.convert_workbook(sheets, filter_sheets=True)
    print(f"  文本总长度: {len(text):,} 字符")
    print(f"  总行数: {len(text.splitlines())}\n")

    # 展示关键片段
    print("  ── 基本信息 Sheet 前 10 行 ──\n")
    for name, sd in sheets.items():
        if "basic" in name.lower():
            sheet_text = converter.convert_sheet(sd)
            for line in sheet_text.splitlines()[:12]:
                print(f"  {line}")
            break

    print(f"\n  ── 服务矩阵 Sheet 前 10 行 ──\n")
    for name, sd in sheets.items():
        if "service" in name.lower() and "diagnostic" in name.lower():
            sheet_text = converter.convert_sheet(sd)
            for line in sheet_text.splitlines()[:10]:
                print(f"  {line}")
            break

    return text


def demo_generate(excel_path: str, service_id: str, config_path: str = "config.yaml"):
    """演示完整生成流程：Excel 文本 → LLM 生成测试用例。"""

    from src.uds_agent.generate_pipeline import UDSGeneratePipeline

    separator(f"完整生成流程: 服务 {service_id}")

    pipeline = UDSGeneratePipeline(config_path=config_path)

    print(f"  正在生成测试用例...\n")
    start = time.time()

    result = pipeline.generate(
        excel_path=excel_path,
        service_id=service_id,
        domain="App",
    )
    elapsed = time.time() - start

    if result.meta.get("error"):
        print(f"  错误: {result.meta['error']}")
        return

    print(f"  服务: {result.service_id} ({result.service_name})")
    print(f"  生成用例: {result.total_count} 条")
    print(f"  耗时: {elapsed:.1f}s")
    print(f"  LLM: {result.meta.get('provider', '?')} / {result.meta.get('model', '?')}")

    if result.test_cases:
        print(f"\n  前 5 条用例:")
        for tc in result.test_cases[:5]:
            print(f"    [{tc.case_id}] {tc.case_name}")

    # 保存完整 JSON
    output = result.model_dump()
    out_path = Path("output/generate_result.json")
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  完整 JSON 已保存到: {out_path}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="UDS ASSISTANT 演示")
    parser.add_argument("--input", default="input/Het Diagnostic Parameters_V1.7_20250421.xlsx")
    parser.add_argument("--service", default="0x10", help="目标服务 ID（默认 0x10）")
    parser.add_argument("--generate", action="store_true", help="运行完整生成流程（需要 API Key）")
    args = parser.parse_args()

    print("╔══════════════════════════════════════════════════════════╗")
    print("║         UDS 诊断测试用例自动生成智能体 — 演示            ║")
    print("╚══════════════════════════════════════════════════════════╝")

    # 模块1：Excel 解析
    demo_module1(args.input)

    # 完整生成流程（可选）
    if args.generate:
        demo_generate(args.input, args.service)
    else:
        separator("生成流程跳过")
        print("  如需运行完整生成流程:")
        print(f"    python demo.py --generate --service {args.service}")

    print()


if __name__ == "__main__":
    main()
