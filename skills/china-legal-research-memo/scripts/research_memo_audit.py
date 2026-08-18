#!/usr/bin/env python3
"""Mechanical completeness audit for Chinese legal research memoranda.

This script checks structure and traceability signals in Markdown, text, and DOCX
files.  It does not assess whether a legal conclusion is correct.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


@dataclass
class Finding:
    level: str
    code: str
    message: str
    locations: list[str]


def read_docx(path: Path) -> tuple[str, list[str]]:
    """Extract readable text and external hyperlink targets from a DOCX."""
    with zipfile.ZipFile(path) as archive:
        document = ET.fromstring(archive.read("word/document.xml"))
        paragraphs: list[str] = []
        for paragraph in document.iter(f"{{{W_NS}}}p"):
            text = "".join(node.text or "" for node in paragraph.iter(f"{{{W_NS}}}t"))
            text = text.strip()
            if text:
                paragraphs.append(text)

        links: list[str] = []
        rel_path = "word/_rels/document.xml.rels"
        if rel_path in archive.namelist():
            rels = ET.fromstring(archive.read(rel_path))
            for rel in rels.iter(f"{{{PKG_REL_NS}}}Relationship"):
                if rel.attrib.get("TargetMode") == "External":
                    target = rel.attrib.get("Target", "").strip()
                    if target:
                        links.append(target)
        return "\n".join(paragraphs), sorted(set(links))


def read_input(path: Path) -> tuple[str, list[str]]:
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return read_docx(path)
    if suffix in {".md", ".markdown", ".txt"}:
        return path.read_text(encoding="utf-8-sig"), []
    raise ValueError(f"unsupported file type: {suffix or '(none)'}")


def unique_matches(pattern: str, text: str, flags: int = 0) -> list[str]:
    return sorted({m.group(0).strip() for m in re.finditer(pattern, text, flags)})


def find_locations(pattern: str, lines: list[str], flags: int = 0, limit: int = 12) -> list[str]:
    found: list[str] = []
    compiled = re.compile(pattern, flags)
    for line_no, line in enumerate(lines, 1):
        if compiled.search(line):
            excerpt = re.sub(r"\s+", " ", line).strip()
            found.append(f"line {line_no}: {excerpt[:100]}")
            if len(found) >= limit:
                break
    return found


def add_finding(
    findings: list[Finding], level: str, code: str, message: str, locations: Iterable[str] = ()
) -> None:
    findings.append(Finding(level, code, message, list(locations)))


def section_present(text: str, alternatives: list[str]) -> bool:
    head_pattern = r"(?m)^\s*(?:#{1,6}\s*)?(?:[一二三四五六七八九十]+[、.]|（[一二三四五六七八九十]+）|\d+[.、])?\s*"
    return bool(re.search(head_pattern + r"(?:" + "|".join(alternatives) + r")", text))


def nearby_source_warnings(lines: list[str]) -> list[str]:
    assertion = re.compile(r"(应当|必须|不得|禁止|有权|无需|可以依法|应予|不予|属于|构成)")
    source = re.compile(
        r"(《[^》]{2,80}》|第[〇零一二三四五六七八九十百千万两\d]+条|"
        r"[（(〔\[]20\d{2}[）)〕\]][^\n]{0,50}?号|https?://|法宝|元典|法院|监管|处罚决定)"
    )
    warned: list[str] = []
    for index, line in enumerate(lines):
        if len(line.strip()) < 12 or not assertion.search(line):
            continue
        window = " ".join(lines[max(0, index - 2) : min(len(lines), index + 2)])
        if not source.search(window):
            warned.append(f"line {index + 1}: {re.sub(r'\s+', ' ', line).strip()[:100]}")
        if len(warned) >= 15:
            break
    return warned


def audit(path: Path) -> dict:
    text, docx_links = read_input(path)
    normalized = text.replace("\u3000", " ")
    lines = [line.strip() for line in normalized.splitlines() if line.strip()]
    findings: list[Finding] = []

    if len(normalized.strip()) < 300:
        add_finding(findings, "error", "TEXT_TOO_SHORT", "正文少于 300 字，可能未成功提取或不是完整调研文件。")

    section_checks = {
        "background": section_present(normalized, ["(?:问题|事项|调研)?背景", "目的与范围", "调研范围"]),
        "issues": section_present(normalized, ["(?:调研|法律|主要)?问题", "委托事项", "研究事项"]),
        "analysis": section_present(normalized, ["(?:相关|法律|具体)?分析", "法律依据", "相关规定", "论证"]),
        "conclusion_or_advice": section_present(normalized, ["(?:初步|总体|主要)?结论", "(?:合规|实施)?建议", "风险及建议"]),
        "sources_or_appendix": section_present(normalized, ["主要依据", "来源", "附件", "案例", "法规"]),
    }

    if not section_checks["analysis"]:
        add_finding(findings, "error", "MISSING_ANALYSIS", "未识别到法律分析或相关规定部分。")
    if not section_checks["conclusion_or_advice"]:
        add_finding(
            findings,
            "warning",
            "MISSING_CONCLUSION",
            "未识别到单独的结论或建议部分；请确认各问题中已有明确答复。",
        )
    if not section_checks["background"]:
        add_finding(findings, "warning", "MISSING_BACKGROUND", "未识别到背景、目的或调研范围部分。")
    if not section_checks["issues"]:
        add_finding(findings, "warning", "MISSING_ISSUES", "未识别到明确的问题或委托事项部分。")

    hard_placeholders = r"(?i)(\bTODO\b|\bFIXME\b|\bTBD\b|X{3,}|_{4,}|\[\s*(?:待|填写|补充|核实|确认|insert)|【\s*(?:待|填写|补充|核实|确认))"
    hard_locations = find_locations(hard_placeholders, lines)
    if hard_locations:
        add_finding(findings, "error", "UNRESOLVED_PLACEHOLDER", "存在未清理的模板占位符。", hard_locations)

    review_markers = r"(待核实|待确认|待补充|尚待|无法确认|暂未发现|未检索到)"
    review_locations = find_locations(review_markers, lines)
    if review_locations:
        add_finding(
            findings,
            "warning",
            "REVIEW_MARKERS",
            "正文保留待确认或研究局限标记；请确认其为有意披露，而非遗漏。",
            review_locations,
        )

    law_names = unique_matches(r"《[^》\n]{2,80}》", normalized)
    articles = unique_matches(r"第[〇零一二三四五六七八九十百千万两\d]+条(?:之[一二三四五六七八九十\d]+)?", normalized)
    case_numbers = unique_matches(r"[（(〔\[]20\d{2}[）)〕\]][^\s，。；：]{1,55}?号", normalized)
    dates = unique_matches(
        r"(?:19|20)\d{2}[年./-](?:0[1-9]|1[0-2]|[1-9])[月./-](?:0[1-9]|[12]\d|3[01]|[1-9])日?",
        normalized,
    )
    text_links = unique_matches(r"https?://[^\s<>()\[\]，。；]+", normalized)
    links = sorted(set(text_links + docx_links))

    if law_names and not articles:
        add_finding(findings, "warning", "NO_ARTICLE_PINPOINT", "识别到法规名称，但未识别到具体条文定位。")
    if not law_names:
        add_finding(findings, "warning", "NO_LAW_NAMES", "未识别到书名号形式的法规名称。")
    if not links:
        add_finding(findings, "warning", "NO_LINKS", "未识别到外部链接；请确认法宝、元典或官方来源是否另有台账。")
    if not dates:
        add_finding(findings, "warning", "NO_DATES", "未识别到完整日期；请确认基准日期和核验日期。")

    unsupported = nearby_source_warnings(lines)
    if unsupported:
        add_finding(
            findings,
            "warning",
            "ASSERTION_WITHOUT_NEARBY_SOURCE",
            "部分义务性或定性表述附近未识别到来源信号，请人工检查主张—来源对应。",
            unsupported,
        )

    headings = [
        line
        for line in lines
        if re.match(r"^(?:#{1,6}\s+|[一二三四五六七八九十]+[、.]|（[一二三四五六七八九十]+）|\d+[.、])", line)
    ]
    repeated_headings = sorted([heading for heading, count in Counter(headings).items() if count > 1])
    if repeated_headings:
        add_finding(
            findings,
            "warning",
            "DUPLICATE_HEADINGS",
            "存在完全相同的标题，请确认编号或复制粘贴是否有误。",
            repeated_headings[:12],
        )

    counts = Counter(finding.level for finding in findings)
    return {
        "schema_version": 1,
        "file": str(path.resolve()),
        "disclaimer": "This is a mechanical completeness audit, not a legal opinion or substantive legal review.",
        "status": "fail" if counts["error"] else "pass_with_warnings" if counts["warning"] else "pass",
        "summary": {
            "characters": len(normalized),
            "nonempty_lines": len(lines),
            "headings_detected": len(headings),
            "law_names": len(law_names),
            "article_references": len(articles),
            "case_numbers": len(case_numbers),
            "dates": len(dates),
            "links": len(links),
            "errors": counts["error"],
            "warnings": counts["warning"],
        },
        "section_checks": section_checks,
        "inventory": {
            "law_names": law_names,
            "article_references": articles,
            "case_numbers": case_numbers,
            "dates": dates,
            "links": links,
        },
        "findings": [asdict(finding) for finding in findings],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Markdown, text, or DOCX memorandum")
    parser.add_argument("--output", type=Path, help="write JSON report to this path")
    parser.add_argument("--strict", action="store_true", help="treat warnings as a failing exit status")
    args = parser.parse_args()

    if not args.input.is_file():
        parser.error(f"input file not found: {args.input}")

    try:
        report = audit(args.input)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, ET.ParseError) as exc:
        report = {
            "schema_version": 1,
            "file": str(args.input.resolve()),
            "status": "fail",
            "summary": {"errors": 1, "warnings": 0},
            "findings": [
                asdict(Finding("error", "READ_FAILURE", f"无法读取或解析文件：{exc}", []))
            ],
        }

    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)

    warnings = int(report.get("summary", {}).get("warnings", 0))
    if report.get("status") == "fail" or (args.strict and warnings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
