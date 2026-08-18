#!/usr/bin/env python3
"""Create or audit a claim-to-source ledger for a Chinese legal memorandum."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path


COLUMNS = [
    "claim_id",
    "issue_id",
    "claim",
    "claim_type",
    "source_level",
    "source_title",
    "pinpoint",
    "url_or_local_path",
    "current_status",
    "checked_on",
    "supports_or_limits",
    "note",
]

CLAIM_TYPES = {
    "fact",
    "rule",
    "case_holding",
    "regulatory_practice",
    "secondary_view",
    "inference",
    "recommendation",
}

SOURCE_LEVELS = {
    "project_material",
    "primary_norm",
    "official_practice",
    "case_fulltext",
    "legal_database",
    "secondary",
    "internal_reasoning",
}

EFFECTS = {"support", "limit", "neutral", "conflict"}
SOURCE_REQUIRED = {"fact", "rule", "case_holding", "regulatory_practice", "secondary_view"}
PINPOINT_REQUIRED = {"fact", "rule", "case_holding"}
DATE_RE = re.compile(r"^20\d{2}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])$")


@dataclass
class Finding:
    level: str
    code: str
    message: str
    row: int | None = None
    claim_id: str | None = None


def write_template(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing file: {path}")
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerow(
            {
                "claim_id": "C001",
                "issue_id": "I01",
                "claim": "示例行，使用前删除：某项已确认事实或法律主张",
                "claim_type": "fact",
                "source_level": "project_material",
                "source_title": "示例材料名称",
                "pinpoint": "第1页或第1条",
                "url_or_local_path": "项目内相对路径",
                "current_status": "confirmed",
                "checked_on": "2026-08-10",
                "supports_or_limits": "support",
                "note": "记录事实状态、冲突或引用用途",
            }
        )


def audit(path: Path) -> dict:
    findings: list[Finding] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        missing_headers = [column for column in COLUMNS if column not in headers]
        if missing_headers:
            findings.append(
                Finding("error", "MISSING_COLUMNS", "缺少必填列：" + ", ".join(missing_headers))
            )
            rows: list[dict[str, str]] = []
        else:
            rows = [{key: (value or "").strip() for key, value in row.items()} for row in reader]

    claim_ids: set[str] = set()
    issue_effects: dict[str, set[str]] = defaultdict(set)
    issue_counts: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()

    for row_no, row in enumerate(rows, 2):
        claim_id = row.get("claim_id", "")
        issue_id = row.get("issue_id", "")
        claim_type = row.get("claim_type", "")
        source_level = row.get("source_level", "")
        effect = row.get("supports_or_limits", "")

        if not claim_id:
            findings.append(Finding("error", "MISSING_CLAIM_ID", "主张编号为空。", row_no))
        elif claim_id in claim_ids:
            findings.append(Finding("error", "DUPLICATE_CLAIM_ID", "主张编号重复。", row_no, claim_id))
        else:
            claim_ids.add(claim_id)

        if not issue_id:
            findings.append(Finding("error", "MISSING_ISSUE_ID", "问题编号为空。", row_no, claim_id or None))
        if not row.get("claim"):
            findings.append(Finding("error", "MISSING_CLAIM", "主张内容为空。", row_no, claim_id or None))

        if claim_type not in CLAIM_TYPES:
            findings.append(
                Finding(
                    "error",
                    "INVALID_CLAIM_TYPE",
                    "claim_type 应为：" + ", ".join(sorted(CLAIM_TYPES)),
                    row_no,
                    claim_id or None,
                )
            )
        if source_level not in SOURCE_LEVELS:
            findings.append(
                Finding(
                    "error",
                    "INVALID_SOURCE_LEVEL",
                    "source_level 应为：" + ", ".join(sorted(SOURCE_LEVELS)),
                    row_no,
                    claim_id or None,
                )
            )
        if effect not in EFFECTS:
            findings.append(
                Finding(
                    "error",
                    "INVALID_EFFECT",
                    "supports_or_limits 应为 support、limit、neutral 或 conflict。",
                    row_no,
                    claim_id or None,
                )
            )

        if claim_type in SOURCE_REQUIRED:
            for field, label in (
                ("source_title", "来源标题"),
                ("url_or_local_path", "链接或本地路径"),
                ("checked_on", "核验日期"),
            ):
                if not row.get(field):
                    findings.append(
                        Finding("error", f"MISSING_{field.upper()}", f"{label}为空。", row_no, claim_id or None)
                    )

        if claim_type in PINPOINT_REQUIRED and not row.get("pinpoint"):
            findings.append(
                Finding("error", "MISSING_PINPOINT", "事实、规则或案例主张缺少页码、条款或段落定位。", row_no, claim_id or None)
            )

        checked_on = row.get("checked_on", "")
        if checked_on and not DATE_RE.match(checked_on):
            findings.append(
                Finding("error", "INVALID_DATE", "核验日期应使用 YYYY-MM-DD 格式。", row_no, claim_id or None)
            )

        if claim_type in {"rule", "case_holding", "regulatory_practice"} and not row.get("current_status"):
            findings.append(
                Finding("error", "MISSING_CURRENT_STATUS", "规范、案例或监管实践缺少现行性或状态说明。", row_no, claim_id or None)
            )

        if claim_type == "inference" and not row.get("note"):
            findings.append(
                Finding("warning", "INFERENCE_WITHOUT_REASON", "推断行应在 note 中写明前提和推理步骤。", row_no, claim_id or None)
            )
        if claim_type == "recommendation" and not row.get("note"):
            findings.append(
                Finding("warning", "RECOMMENDATION_WITHOUT_BASIS", "建议行应在 note 中写明依赖的规则、事实或风险选择。", row_no, claim_id or None)
            )

        if issue_id:
            issue_counts[issue_id] += 1
            if effect in EFFECTS:
                issue_effects[issue_id].add(effect)
        if claim_type:
            type_counts[claim_type] += 1
        if source_level:
            source_counts[source_level] += 1

    if not rows:
        findings.append(Finding("error", "EMPTY_LEDGER", "台账没有数据行。"))

    for issue_id, effects in sorted(issue_effects.items()):
        if not effects.intersection({"limit", "conflict"}):
            findings.append(
                Finding(
                    "warning",
                    "NO_LIMITING_SOURCE",
                    f"问题 {issue_id} 未记录限制或冲突来源，请确认已完成反向检索。",
                )
            )

    levels = Counter(finding.level for finding in findings)
    return {
        "schema_version": 1,
        "file": str(path.resolve()),
        "disclaimer": "This audit checks ledger fields only; it does not validate legal relevance or correctness.",
        "status": "fail" if levels["error"] else "pass_with_warnings" if levels["warning"] else "pass",
        "summary": {
            "rows": len(rows),
            "issues": len(issue_counts),
            "errors": levels["error"],
            "warnings": levels["warning"],
            "claim_types": dict(sorted(type_counts.items())),
            "source_levels": dict(sorted(source_counts.items())),
            "rows_by_issue": dict(sorted(issue_counts.items())),
        },
        "findings": [asdict(finding) for finding in findings],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("ledger", nargs="?", type=Path, help="CSV ledger to audit")
    group.add_argument("--write-template", type=Path, help="create a new CSV ledger template")
    parser.add_argument("--output", type=Path, help="write JSON audit report")
    parser.add_argument("--strict", action="store_true", help="treat warnings as a failing exit status")
    args = parser.parse_args()

    if args.write_template:
        try:
            write_template(args.write_template)
        except OSError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(str(args.write_template.resolve()))
        return 0

    if not args.ledger or not args.ledger.is_file():
        parser.error(f"ledger file not found: {args.ledger}")

    try:
        report = audit(args.ledger)
    except (OSError, csv.Error) as exc:
        report = {
            "schema_version": 1,
            "file": str(args.ledger.resolve()),
            "status": "fail",
            "summary": {"rows": 0, "errors": 1, "warnings": 0},
            "findings": [asdict(Finding("error", "READ_FAILURE", f"无法读取台账：{exc}"))],
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
