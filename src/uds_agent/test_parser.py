"""LLM 输出 → 结构化测试用例解析器。

期望的 LLM 输出格式（由 user message 中的格式模板强制）：

### N.M 测试类别名称
#### N.M.N 用例名称
- **Case ID**: Diag_0xNN_Phy_NNN
- **Steps**:
  1. Send DiagBy[...]Data[...];
- **Expected Output**:
  1. Check DiagData[...]Within[...]ms;

也兼容全角冒号格式作为 fallback。
"""

from __future__ import annotations

import re

from .test_schemas import SectionSummary, TestCaseRow

# Case ID pattern
RE_CASE_ID = re.compile(r"Diag_(0x[0-9A-Fa-f]{2})_(Phy|Fun)_(\d{3})")

# Section header (legacy format B)
RE_SECTION = re.compile(r"^--service ID (0x[0-9A-Fa-f]{2})\s+(.+)$")

# Summary table header
RE_SUMMARY = re.compile(r"^##\s*用例统计汇总")

# Markdown field markers (flexible matching)
RE_MD_CASE_ID = re.compile(r"[-*]?\s*\*{0,2}\s*Case\s*ID\s*\*{0,2}\s*:\s*(.+)")
RE_MD_CASE_NAME = re.compile(r"[-*]?\s*\*{0,2}\s*(?:Case\s*Name|Case名称|用例名称)\s*\*{0,2}\s*:\s*(.+)")
RE_MD_STEPS = re.compile(r"[-*]?\s*\*{0,2}\s*(?:Steps|测试步骤|Test\s*Procedure)\s*\*{0,2}\s*:")
RE_MD_EXPECTED = re.compile(r"[-*]?\s*\*{0,2}\s*(?:Expected\s*Output|预期输出)\s*\*{0,2}\s*:")

# Step line: N.action
RE_STEP = re.compile(r"^\d+\.\s+.+")


def parse_test_cases(text: str, service_id: str) -> list[TestCaseRow]:
    """解析 LLM 输出文本为结构化测试用例列表。"""
    cases_text, _ = _split_zones(text)

    if _is_markdown_format(cases_text):
        raw_cases, section_map = _parse_markdown(cases_text)
    else:
        raw_cases, section_map = _parse_colon(cases_text)

    return _assign_sections(raw_cases, section_map, service_id)


def parse_summary(text: str) -> list[SectionSummary]:
    """解析 Zone C 汇总表。"""
    _, summary_text = _split_zones(text)
    if not summary_text:
        return []

    summaries: list[SectionSummary] = []
    in_table = False
    for line in summary_text.split("\n"):
        line = line.strip()
        if line.startswith("|") and "分类" in line:
            in_table = True
            continue
        if line.startswith("|---") or line.startswith("| ---"):
            continue
        if in_table and line.startswith("|"):
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if len(cells) >= 4 and cells[0] and "**" not in cells[0]:
                summaries.append(SectionSummary(
                    section_name=cells[0],
                    physical_count=_parse_count(cells[1]),
                    functional_count=_parse_count(cells[2]),
                    total_count=_parse_count(cells[3]),
                ))
        elif in_table and not line.startswith("|"):
            break
    return summaries


# ---------------------------------------------------------------------------
# Zone splitting
# ---------------------------------------------------------------------------

def _split_zones(text: str) -> tuple[str, str]:
    lines = text.split("\n")
    zone_c_start = len(lines)
    for i, line in enumerate(lines):
        if RE_SUMMARY.match(line.strip()):
            zone_c_start = i
            break
    return "\n".join(lines[:zone_c_start]), "\n".join(lines[zone_c_start:])


def _is_markdown_format(text: str) -> bool:
    for line in text.split("\n"):
        if RE_MD_CASE_ID.match(line.strip()):
            return True
    return False


# ---------------------------------------------------------------------------
# Markdown format parsing
# ---------------------------------------------------------------------------

def _parse_markdown(text: str) -> tuple[list[dict], dict[str, str]]:
    raw_cases: list[dict] = []
    section_map: dict[str, str] = {}

    current_section = ""
    current_case_name = ""
    current_case_id = ""
    current_steps: list[str] = []
    current_expected: list[str] = []
    in_steps = False
    in_expected = False

    def flush():
        nonlocal current_case_id, current_case_name, current_steps, current_expected
        nonlocal in_steps, in_expected
        if current_case_id and RE_CASE_ID.search(current_case_id):
            # If no expected output, extract Check lines from steps
            steps_final = current_steps
            expected_final = current_expected
            if not expected_final:
                steps_final, expected_final = _split_checks(current_steps)

            raw_cases.append({
                "case_id": current_case_id.strip(),
                "case_name": current_case_name.strip(),
                "test_procedure": "\n".join(steps_final),
                "expected_output": "\n".join(expected_final),
                "section_name": current_section,
                "is_boot": "boot" in current_section.lower(),
            })
            section_map[current_case_id.strip()] = current_section
        current_case_id = ""
        current_case_name = ""
        current_steps = []
        current_expected = []
        in_steps = False
        in_expected = False

    for line in text.split("\n"):
        stripped = line.strip()

        # ### header: section or "Case N:"
        if stripped.startswith("### "):
            header = stripped[4:].strip().strip("*").strip()
            if re.match(r"Case\s+\d+", header, re.IGNORECASE):
                flush()
                m = re.match(r"Case\s+\d+\s*[:：]\s*(.+)", header, re.IGNORECASE)
                current_case_name = m.group(1).strip() if m else header
            else:
                flush()
                m = re.match(r"^[\d.]+\s+(.+)$", header)
                current_section = m.group(1) if m else header
            continue

        # #### header: case name
        if stripped.startswith("#### "):
            flush()
            header = stripped[5:].strip().strip("*").strip()
            m = re.match(r"^[\d.]+\s+(.+)$", header)
            current_case_name = m.group(1) if m else header
            continue

        # Case ID
        m = RE_MD_CASE_ID.match(stripped)
        if m:
            saved_name = current_case_name
            flush()
            current_case_id = m.group(1).strip()
            current_case_name = saved_name
            continue

        # Case Name field
        m = RE_MD_CASE_NAME.match(stripped)
        if m:
            current_case_name = m.group(1).strip()
            continue

        # Steps header
        if RE_MD_STEPS.match(stripped):
            in_steps = True
            in_expected = False
            continue

        # Expected Output header
        if RE_MD_EXPECTED.match(stripped):
            in_steps = False
            in_expected = True
            continue

        # Other field marker → stop collecting
        if re.match(r"[-*]?\s*\*{0,2}\s*(?:Objective|Precondition|Postcondition|Priority|Note)", stripped):
            in_steps = False
            in_expected = False
            continue

        # Inline Check lines (when no separate Expected Output section)
        if in_steps:
            check_m = re.match(r"[-*]\s*\*?\s*Check\s*\*?\s*:\s*(.+)", stripped)
            if check_m:
                current_expected.append(check_m.group(1).strip())
                continue

        # Collect content
        if stripped:
            cleaned = _clean_inline(stripped)
            if in_steps:
                if RE_STEP.match(stripped):
                    current_steps.append(cleaned)
                elif current_steps:
                    current_steps[-1] += " " + cleaned
            elif in_expected:
                if RE_STEP.match(stripped):
                    current_expected.append(cleaned)
                elif current_expected:
                    current_expected[-1] += " " + cleaned

    flush()
    return raw_cases, section_map


def _split_checks(steps: list[str]) -> tuple[list[str], list[str]]:
    """If steps contain Check lines, split them into steps and checks."""
    if any("Check " in s for s in steps):
        pure_steps = []
        checks = []
        for s in steps:
            if s.strip().startswith("Check "):
                checks.append(s)
            else:
                pure_steps.append(s)
        if checks:
            return pure_steps, checks
    return steps, []


def _clean_inline(text: str) -> str:
    """Strip backticks and inline annotations."""
    text = text.replace("`", "")
    text = re.sub(r"\s*\([^)]*(?:enter|verify|check|request|send|delay|session)[^)]*\)", "", text, flags=re.IGNORECASE)
    return text.strip()


# ---------------------------------------------------------------------------
# Legacy full-width colon format parsing
# ---------------------------------------------------------------------------

FULL_COLON = "："

def _parse_colon(text: str) -> tuple[list[dict], dict[str, str]]:
    sections: list[tuple[str, str]] = []
    current_name = ""
    current_lines: list[str] = []

    for line in text.split("\n"):
        stripped = line.strip()
        m = RE_SECTION.match(stripped)
        if m:
            if current_name and current_lines:
                sections.append((current_name, "\n".join(current_lines)))
            current_name = m.group(2).strip()
            current_lines = []
        elif stripped == "---":
            continue
        else:
            current_lines.append(line)

    if current_name and current_lines:
        sections.append((current_name, "\n".join(current_lines)))

    raw_cases: list[dict] = []
    section_map: dict[str, str] = {}

    for section_name, block in sections:
        is_boot = "boot" in section_name.lower()
        for case in _parse_colon_cases(block):
            case["section_name"] = section_name
            case["is_boot"] = is_boot
            raw_cases.append(case)
            if case.get("case_id"):
                section_map[case["case_id"]] = section_name

    return raw_cases, section_map


def _parse_colon_cases(block: str) -> list[dict]:
    cases: list[dict] = []
    marker = f"Case ID{FULL_COLON}"
    for frag in block.split(marker)[1:]:
        frag = frag.strip()
        if not frag:
            continue
        lines = frag.split("\n")
        case_id = lines[0].strip()
        if not RE_CASE_ID.match(case_id):
            continue
        remaining = "\n".join(lines[1:])
        cases.append({
            "case_id": case_id,
            "case_name": _extract_colon_field(remaining, f"Case名称{FULL_COLON}"),
            "test_procedure": _extract_colon_steps(remaining, f"测试步骤{FULL_COLON}"),
            "expected_output": _extract_colon_steps(remaining, f"预期输出{FULL_COLON}"),
        })
    return cases


def _extract_colon_field(text: str, marker: str) -> str:
    markers = [f"Case ID{FULL_COLON}", f"Case名称{FULL_COLON}", f"测试步骤{FULL_COLON}", f"预期输出{FULL_COLON}"]
    idx = text.find(marker)
    if idx == -1:
        return ""
    start = idx + len(marker)
    end = min((text.find(m, start) for m in markers if text.find(m, start) > start), default=len(text))
    return text[start:end].strip()


def _extract_colon_steps(text: str, marker: str) -> str:
    raw = _extract_colon_field(text, marker)
    lines = []
    for line in raw.split("\n"):
        s = line.strip()
        if s and RE_STEP.match(s):
            lines.append(s)
        elif s and not s.startswith(("Case", "测试", "预期")) and lines:
            lines[-1] += " " + s
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Section assignment
# ---------------------------------------------------------------------------

def _assign_sections(
    raw_cases: list[dict],
    section_map: dict[str, str],
    service_id: str,
) -> list[TestCaseRow]:
    if not raw_cases:
        return []

    ORDER = ["Application_Physical", "Application_Functional", "Bootloader_Physical", "Bootloader_Functional"]
    grouped: dict[str, list[tuple[int, dict]]] = {k: [] for k in ORDER}

    for idx, raw in enumerate(raw_cases):
        case_id = raw.get("case_id", "")
        case_name = raw.get("case_name", "")
        section_name = raw.get("section_name", "")

        is_boot = raw.get("is_boot", False) or "boot" in section_name.lower() or "boot" in case_name.lower()

        m = RE_CASE_ID.search(case_id)
        addr = m.group(2) if m else "Phy"
        domain = "Bootloader" if is_boot else "Application"
        addr_label = "Physical" if addr == "Phy" else "Functional"
        key = f"{domain}_{addr_label}"
        if key not in grouped:
            key = "Application_Physical"
        grouped[key].append((idx, raw))

    # Assign section numbers
    sec_nums: dict[str, int] = {}
    n = 1
    for k in ORDER:
        if grouped[k]:
            sec_nums[k] = n
            n += 1

    # Assign subsection numbers per group
    sub_nums: dict[str, dict[str, int]] = {k: {} for k in ORDER}

    cases: list[TestCaseRow] = []
    seq = 1

    for gk in ORDER:
        if not grouped[gk]:
            continue
        sn = sec_nums[gk]
        domain = gk.split("_")[0]
        addr = gk.split("_")[1]
        addr_text = "Physical" if addr == "Physical" else "Functional"
        sec_title = f"{sn}.{domain} Service_{addr_text} Addressing"

        for _, raw in grouped[gk]:
            sname = raw.get("section_name", "")
            if sname not in sub_nums[gk]:
                sub_nums[gk][sname] = len(sub_nums[gk]) + 1
            sub_sn = sub_nums[gk][sname]
            sub_title = f"{sn}.{sub_sn} {sname}"

            cases.append(TestCaseRow(
                section=sec_title,
                subsection=sub_title,
                sequence_number=seq,
                case_id=raw.get("case_id", ""),
                case_name=raw.get("case_name", ""),
                priority=_infer_priority(raw.get("case_name", "")),
                test_procedure=raw.get("test_procedure", ""),
                expected_output=raw.get("expected_output", ""),
            ))
            seq += 1

    return cases


def _infer_priority(case_name: str) -> str:
    name = case_name.lower()
    if "traversal" in name:
        return "Medium"
    if any(kw in name for kw in ("incorrect", "dlc", "sf_dl", "nrc priority")):
        return "Low"
    if "reset" in name and "session" in name:
        return "Low"
    if "s3" in name and "timer" in name:
        return "Low"
    return "High"


def _parse_count(text: str) -> int:
    m = re.match(r"(\d+)", text.strip().replace("**", ""))
    return int(m.group(1)) if m else 0
