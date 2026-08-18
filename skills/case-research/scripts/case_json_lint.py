#!/usr/bin/env python3
"""Lint case-research JSON archives."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


VALID_STATUSES = {"complete", "partial", "snippet_only", "metadata_only"}


def get(data: dict[str, Any], dotted: str, default: Any = "") -> Any:
    cur: Any = data
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return default
        cur = cur.get(part, default)
    return cur


def lint_one(path: Path, min_complete_chars: int) -> tuple[bool, list[str]]:
    issues: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, [f"无法读取 JSON: {exc}"]

    status = data.get("full_text_status")
    if status not in VALID_STATUSES:
        issues.append(f"full_text_status 非法或缺失: {status!r}")

    full_text = get(data, "sections.full_text", "") or ""
    reasoning = get(data, "sections.court_reasoning", "") or ""
    result = get(data, "sections.judgment_result", "") or ""

    if status == "complete":
        if len(full_text) < min_complete_chars:
            issues.append(f"complete 但 full_text 字数过短: {len(full_text)} < {min_complete_chars}")
        if not reasoning:
            issues.append("complete 但缺少 sections.court_reasoning")
        if not result:
            issues.append("complete 但缺少 sections.judgment_result")
        if data.get("not_complete_reason") or data.get("next_retrieval_steps"):
            issues.append("complete 不应同时填写 not_complete_reason/next_retrieval_steps")
    else:
        if not data.get("not_complete_reason") and status in {"partial", "snippet_only", "metadata_only"}:
            issues.append(f"{status} 应填写 not_complete_reason")

    integrity = data.get("integrity") or {}
    recorded_count = integrity.get("full_text_char_count")
    if recorded_count not in (None, 0, len(full_text)):
        issues.append(f"integrity.full_text_char_count 与实际不一致: {recorded_count} != {len(full_text)}")

    recorded_hash = integrity.get("sha256")
    if full_text and recorded_hash:
        actual_hash = hashlib.sha256(full_text.encode("utf-8")).hexdigest()
        if recorded_hash != actual_hash:
            issues.append("integrity.sha256 与 sections.full_text 不一致")

    source_url = get(data, "source.source_url", "") or get(data, "source.verification_url", "")
    if not source_url:
        issues.append("缺少 source.source_url 或 source.verification_url")
    if not get(data, "case_metadata.case_number", ""):
        issues.append("缺少 case_metadata.case_number")
    if not get(data, "case_metadata.court", ""):
        issues.append("缺少 case_metadata.court")

    materials = data.get("source_materials") or []
    if isinstance(materials, list):
        for idx, item in enumerate(materials, start=1):
            if not isinstance(item, dict):
                continue
            if item.get("url") and item.get("used_for") != "排除":
                if not item.get("viewpoint_summary"):
                    issues.append(f"source_materials[{idx}] 有 URL 但缺少 viewpoint_summary")
                if not item.get("cited_rules_summary"):
                    issues.append(f"source_materials[{idx}] 有 URL 但缺少 cited_rules_summary")
            notes = str(item.get("notes") or "")
            if notes in {"规则背景", "文章线索", "可作规则背景"}:
                issues.append(f"source_materials[{idx}] notes 过于空泛: {notes}")

    return not issues, issues


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 case-research 案例 JSON 完整性")
    parser.add_argument("paths", nargs="+", help="JSON 文件或目录；目录会递归扫描 *.json")
    parser.add_argument("--min-complete-chars", type=int, default=3000, help="complete 全文最小字数，默认 3000")
    args = parser.parse_args()

    files: list[Path] = []
    for raw in args.paths:
        p = Path(raw)
        if p.is_dir():
            files.extend(sorted(p.rglob("*.json")))
        else:
            files.append(p)

    ok_all = True
    for file in files:
        ok, issues = lint_one(file, args.min_complete_chars)
        if ok:
            print(f"OK {file}")
        else:
            ok_all = False
            print(f"FAIL {file}")
            for issue in issues:
                print(f"  - {issue}")
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
