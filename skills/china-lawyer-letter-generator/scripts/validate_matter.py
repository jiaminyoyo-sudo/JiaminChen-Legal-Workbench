#!/usr/bin/env python3
"""Validate lawyer-letter matter JSON and the fixed 11-part issuance structure."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ALLOWED_STATUS = {"draft", "final"}
ALLOWED_DECISIONS = {
    "confirmed_with_evidence",
    "confirmed_without_evidence",
    "qualify",
    "omit",
}
PLACEHOLDER_RE = re.compile(
    r"待确认|待补充|待核|待列明|待根据|待写明|TBD|TODO|\bX{2,}\b|\[\[.*?\]\]|"
    r"〔[^〕]*(?:待|确认|补充|编号|填写|核实)[^〕]*〕",
    re.IGNORECASE,
)


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _has_content(value: Any) -> bool:
    if _nonempty(value):
        return True
    if isinstance(value, list):
        return any(_nonempty(item) or (isinstance(item, dict) and _nonempty(item.get("text"))) for item in value)
    return False


def _find_placeholders(value: Any, path: str = "document") -> list[str]:
    found: list[str] = []
    if isinstance(value, str):
        if PLACEHOLDER_RE.search(value):
            found.append(path)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_find_placeholders(item, f"{path}[{index}]"))
    elif isinstance(value, dict):
        for key, item in value.items():
            found.extend(_find_placeholders(item, f"{path}.{key}"))
    return found


def _draft_or_final(
    *,
    status: str,
    present: bool,
    draft_message: str,
    final_message: str,
    errors: list[str],
    warnings: list[str],
) -> None:
    if present:
        return
    if status == "final":
        errors.append(final_message)
    else:
        warnings.append(draft_message)


def validate(data: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    status = data.get("status", "draft")
    if status not in ALLOWED_STATUS:
        errors.append("status 只能是 draft 或 final")
        status = "draft"

    for field, label in (
        ("purpose", "签发目的"),
        ("client", "委托人"),
        ("recipient", "收件人"),
        ("matter", "事由或法律关系"),
        ("requested_outcome", "委托人诉求"),
        ("nonperformance_consequence", "不履行后果"),
    ):
        _draft_or_final(
            status=status,
            present=_nonempty(data.get(field)),
            draft_message=f"缺少{label}（{field}），审阅稿将保留提示",
            final_message=f"签发稿缺少{label}（{field}）",
            errors=errors,
            warnings=warnings,
        )

    recipient_address = data.get("recipient_address")
    if not _nonempty(recipient_address):
        warnings.append("尚未核实收件地址；实际送达前须据实补充")

    strategy = data.get("strategy_analysis")
    if not isinstance(strategy, dict):
        strategy = {}
    for field, label in (
        ("advantages", "委托人优势"),
        ("disadvantages", "委托人劣势"),
        ("risks", "主要风险"),
        ("goal_fit", "律师函能否实现签发目的"),
    ):
        _draft_or_final(
            status=status,
            present=_has_content(strategy.get(field)),
            draft_message=f"尚未记录{label}（strategy_analysis.{field}）",
            final_message=f"签发前未完成{label}分析（strategy_analysis.{field}）",
            errors=errors,
            warnings=warnings,
        )

    facts = data.get("facts", [])
    if not isinstance(facts, list):
        errors.append("facts 必须是数组")
        facts = []

    for index, fact in enumerate(facts):
        prefix = f"facts[{index}]"
        if not isinstance(fact, dict):
            errors.append(f"{prefix} 必须是对象")
            continue
        if not _nonempty(fact.get("statement")):
            errors.append(f"{prefix}.statement 不能为空")
        include = bool(fact.get("include_in_letter", True))
        evidence = fact.get("evidence", [])
        needed = fact.get("basic_evidence_needed", [])
        decision = fact.get("lawyer_decision")
        if not isinstance(evidence, list):
            errors.append(f"{prefix}.evidence 必须是数组")
            evidence = []
        if not isinstance(needed, list):
            errors.append(f"{prefix}.basic_evidence_needed 必须是数组")
            needed = []
        if include and not evidence:
            if needed:
                warnings.append(
                    f"{prefix} 尚无现有证据；请律师确认是否具备基础证据："
                    + "、".join(str(item) for item in needed if str(item).strip())
                )
            else:
                warnings.append(f"{prefix} 尚无现有证据，且未列基础应有证据")
        if decision is not None and decision not in ALLOWED_DECISIONS:
            errors.append(f"{prefix}.lawyer_decision 取值无效")
        if include and decision == "omit":
            errors.append(f"{prefix} 同时设置 include_in_letter=true 和 lawyer_decision=omit")
        if status == "final" and include and decision is None:
            errors.append(f"{prefix} 拟写入签发稿但尚无律师选择")
        elif status == "draft" and include and decision is None:
            warnings.append(f"{prefix} 拟写入审阅稿，尚待律师选择表述方式")
        if decision == "confirmed_with_evidence" and not evidence:
            errors.append(f"{prefix} 标记为已有证据确认，但 evidence 为空")

    legal_sources = data.get("legal_sources", [])
    if not isinstance(legal_sources, list):
        errors.append("legal_sources 必须是数组")
        legal_sources = []
    for index, source in enumerate(legal_sources):
        prefix = f"legal_sources[{index}]"
        if not isinstance(source, dict):
            errors.append(f"{prefix} 必须是对象")
            continue
        if status == "final" and source.get("verified") is not True:
            errors.append(f"{prefix} 拟用于签发稿但尚未核验")
        elif source.get("verified") is not True:
            warnings.append(f"{prefix} 尚未核验，不得作为确定法律依据写入正文")

    document = data.get("document")
    if not isinstance(document, dict):
        errors.append("document 必须是对象")
        document = {}

    required_document_fields = (
        ("title", "标题"),
        ("reference_no", "案号"),
        ("subject", "摘要"),
        ("recipient_line", "收件人行"),
        ("opening", "首部"),
        ("basic_facts", "基本事实"),
        ("legal_liability", "法律责任"),
        ("lawyer_opinion", "本律师意见"),
        ("closing", "结尾"),
        ("firm", "律所名称"),
        ("issue_date", "签发日期"),
        ("stamp_note", "盖章及骑缝章提示"),
    )
    for field, label in required_document_fields:
        _draft_or_final(
            status=status,
            present=_has_content(document.get(field)),
            draft_message=f"审阅稿缺少{label}（document.{field}），生成时将使用固定结构或提示",
            final_message=f"签发稿缺少{label}（document.{field}）",
            errors=errors,
            warnings=warnings,
        )

    subject = str(document.get("subject") or "").strip()
    if subject and not (subject.startswith("关于") and subject.endswith("事宜")):
        warnings.append("document.subject 建议使用“关于……之事宜”或“关于……事宜”")

    main_basis = document.get("main_basis")
    if not isinstance(main_basis, dict):
        main_basis = {}
    for field, label in (("fact_basis", "事实依据"), ("legal_basis", "法律依据")):
        fallback_present = bool(_unique_present(data, field))
        _draft_or_final(
            status=status,
            present=_has_content(main_basis.get(field)) or fallback_present,
            draft_message=f"主要依据缺少{label}（document.main_basis.{field}），生成时将尝试从事项记录提取",
            final_message=f"签发稿主要依据缺少{label}（document.main_basis.{field}）",
            errors=errors,
            warnings=warnings,
        )

    lawyers = document.get("lawyers", [])
    lawyer_names = (
        [str(item).strip() for item in lawyers if str(item).strip()]
        if isinstance(lawyers, list)
        else []
    )
    if status == "final" and len(lawyer_names) != 2:
        errors.append("签发稿必须列明两名经办律师（document.lawyers）")
    elif status == "draft" and len(lawyer_names) != 2:
        warnings.append("审阅稿未列明两名经办律师，生成时将保留两处手签栏")

    attachments = document.get("attachments", [])
    if not isinstance(attachments, list):
        errors.append("document.attachments 必须是数组")
        attachments = []
    no_attachments = document.get("no_attachments") is True
    if attachments and no_attachments:
        errors.append("已有附件时不得同时设置 document.no_attachments=true")
    if status == "final" and not attachments and not no_attachments:
        errors.append("签发稿必须列明附件，或明确设置 document.no_attachments=true")
    elif status == "draft" and not attachments and not no_attachments:
        warnings.append("附件尚未确定，生成时将保留附件提示")

    issuance = data.get("issuance")
    if not isinstance(issuance, dict):
        issuance = {}
    for field, label in (
        ("engagement_completed", "委托手续完备"),
        ("strategy_confirmed_by_client", "签发策略经客户确认"),
        ("letter_confirmed_by_client", "函稿经客户书面确认"),
    ):
        if status == "final" and issuance.get(field) is not True:
            errors.append(f"签发稿未确认：{label}（issuance.{field}）")
        elif status == "draft" and issuance.get(field) is not True:
            warnings.append(f"签发前须确认：{label}（issuance.{field}）")

    if status == "final":
        if data.get("lawyer_confirmed") is not True:
            errors.append("final 状态必须设置 lawyer_confirmed=true")
        for placeholder_path in _find_placeholders(document):
            errors.append(f"签发稿仍含占位符：{placeholder_path}")

    return errors, warnings


def _unique_present(data: dict[str, Any], field: str) -> list[str]:
    if field == "fact_basis":
        result: list[str] = []
        for fact in data.get("facts", []):
            if isinstance(fact, dict) and fact.get("include_in_letter", True):
                result.extend(str(item).strip() for item in fact.get("evidence", []) if str(item).strip())
        return result
    if field == "legal_basis":
        return [
            str(source.get("name") or "").strip()
            for source in data.get("legal_sources", [])
            if isinstance(source, dict)
            and source.get("verified") is True
            and str(source.get("name") or "").strip()
        ]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Matter JSON path")
    parser.add_argument("--report", type=Path, help="Optional JSON report path")
    args = parser.parse_args()

    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"无法读取事项 JSON：{exc}", file=sys.stderr)
        return 2
    if not isinstance(data, dict):
        print("事项 JSON 顶层必须是对象", file=sys.stderr)
        return 2

    errors, warnings = validate(data)
    report = {
        "valid": not errors,
        "status": data.get("status", "draft"),
        "errors": errors,
        "warnings": warnings,
    }
    output = json.dumps(report, ensure_ascii=False, indent=2)
    print(output)
    if args.report:
        args.report.write_text(output + "\n", encoding="utf-8")
    return 2 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
