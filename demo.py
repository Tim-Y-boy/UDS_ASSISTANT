"""UDS ASSISTANT 演示脚本 — 展示模块1（Excel解析）和模块2（LLM提取）的完整流程。

运行方式：
  python demo.py                          # 仅模块1（不需要 API Key）
  python demo.py --with-llm              # 模块1 + 模块2（需要 config.yaml 中有 API Key）
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
    separator("步骤3: 转换为 LLM 可读文本")
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


def demo_module2(excel_text: str, service_id: str, config_path: str = "config.yaml"):
    """演示模块2：LLM 参数提取。"""

    from src.uds_agent.extract_prompt import build_extraction_messages
    from src.uds_agent.llm_client import LLMClient
    from src.uds_agent.response_parser import parse_json_response, validate_extraction

    separator("步骤4: 构建提取提示词")

    system_prompt, user_message = build_extraction_messages(
        excel_text=excel_text,
        service_id=service_id,
        software_domain="App",
    )

    print(f"  系统提示词长度: {len(system_prompt):,} 字符")
    print(f"  用户消息长度:   {len(user_message):,} 字符")
    print(f"  目标服务:       {service_id}")

    print(f"\n  系统提示词前 500 字符:\n")
    print(f"  {system_prompt[:500]}...")

    separator(f"步骤5: 调用 LLM 提取服务 {service_id} 参数")

    client = LLMClient.from_config(config_path=config_path)
    print(f"  可用提供商: {[p.name for p in client._providers]}")
    print(f"  正在调用 LLM...\n")

    start = time.time()
    resp = client.chat(
        system_prompt=system_prompt,
        user_message=user_message,
        temperature=0.05,
        max_tokens=4000,
    )
    elapsed = time.time() - start

    print(f"  提供商: {resp.provider}")
    print(f"  模型:   {resp.model}")
    print(f"  耗时:   {elapsed:.1f}s")
    print(f"  Tokens: {resp.usage.get('total_tokens', 'N/A')}")
    cost = resp.usage.get('cost', 0)
    if cost:
        print(f"  费用:   ${cost:.4f}")

    separator("步骤6: 解析 JSON + Pydantic 校验")

    data = parse_json_response(resp.content)
    result, warnings = validate_extraction(data)

    if warnings:
        print(f"  校验警告 ({len(warnings)}):")
        for w in warnings:
            print(f"    - {w}")
    else:
        print(f"  校验通过，无警告")

    separator("提取结果")

    print(f"  ECU 名称:     {result.basic_info.ecu_name}")
    print(f"  协议:         {result.basic_info.protocol}")
    print(f"  CAN ID Req:   {result.basic_info.canid_req}")
    print(f"  CAN ID Resp:  {result.basic_info.canid_resp}")
    print(f"  CAN ID Func:  {result.basic_info.canid_func}")
    print(f"  P2:           {result.basic_info.p2_ms} ms")
    print(f"  P2*:          {result.basic_info.p2star_ms} ms")
    print(f"  S3:           {result.basic_info.s3_ms} ms")

    print(f"\n  服务 {result.service_matrix.service_id} ({result.service_matrix.service_name}):")
    print(f"  子功能数量: {len(result.service_matrix.subfunctions)}\n")

    for sf in result.service_matrix.subfunctions:
        print(f"    [{sf.subfunction}] {sf.subfunction_name}")
        print(f"      Support={sf.support}  Physical={sf.physical_req}  Functional={sf.functional_req}")
        print(f"      Session: Default={sf.session_default} Extended={sf.session_extended} Programming={sf.session_programming}")
        print(f"      NRC: {sf.nrc_codes}")

    if result.did_list:
        print(f"\n  DID 列表 ({len(result.did_list)} 个):")
        for d in result.did_list[:5]:
            print(f"    {d.did_number} {d.did_name} ({d.byte_length} bytes)")
        if len(result.did_list) > 5:
            print(f"    ... 共 {len(result.did_list)} 个")

    if result.dtc_list:
        print(f"\n  DTC 列表 ({len(result.dtc_list)} 个)")

    if result.routine_list:
        print(f"\n  RID 列表 ({len(result.routine_list)} 个)")

    # 保存完整 JSON
    output = {
        "basic_info": result.basic_info.model_dump(),
        "service_matrix": result.service_matrix.model_dump(),
        "did_list": [d.model_dump() for d in result.did_list],
        "dtc_list": [d.model_dump() for d in result.dtc_list],
        "routine_list": [r.model_dump() for r in result.routine_list],
        "_meta": {
            "provider": resp.provider,
            "model": resp.model,
            "elapsed_seconds": round(elapsed, 2),
            "cost_usd": cost,
        },
    }

    out_path = Path("output/extract_result.json")
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  完整 JSON 已保存到: {out_path}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="UDS ASSISTANT 演示")
    parser.add_argument("--input", default="input/Het Diagnostic Parameters_V1.7_20250421.xlsx")
    parser.add_argument("--service", default="0x10", help="目标服务 ID（默认 0x10）")
    parser.add_argument("--with-llm", action="store_true", help="同时演示模块2（LLM 提取）")
    args = parser.parse_args()

    print("╔══════════════════════════════════════════════════════════╗")
    print("║         UDS 诊断测试用例自动生成智能体 — 演示            ║")
    print("╚══════════════════════════════════════════════════════════╝")

    # 模块1
    excel_text = demo_module1(args.input)

    # 模块2（可选）
    if args.with_llm:
        demo_module2(excel_text, args.service)
    else:
        separator("模块2 跳过")
        print("  如需演示 LLM 提取，运行:")
        print(f"    python demo.py --with-llm --service {args.service}")

    print()


if __name__ == "__main__":
    main()
