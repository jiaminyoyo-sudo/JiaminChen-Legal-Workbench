#!/usr/bin/env python3
"""Generate a Markdown case table from case-research JSON files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


HEADERS = [
    "案例名称",
    "案号/法院/裁判日期",
    "法律关系与核心主张",
    "本院认为",
    "裁判结果",
    "案例链接",
    "线索文章/源素材链接",
]


def clean(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("\r", " ").replace("\n", "<br>").replace("|", "｜").strip()


def first_excerpt(data: dict[str, Any]) -> str:
    excerpts = data.get("excerpts") or []
    if excerpts and isinstance(excerpts, list):
        quote = excerpts[0].get("quote") if isinstance(excerpts[0], dict) else ""
        if quote:
            return quote
    return ((data.get("sections") or {}).get("court_reasoning") or "")[:1200]


def source_materials(data: dict[str, Any]) -> str:
    materials = data.get("source_materials") or []
    rows: list[str] = []
    for item in materials:
        if not isinstance(item, dict):
            continue
        title = item.get("title") or "未命名材料"
        publisher = item.get("publisher") or "发布主体待确认"
        url = item.get("url") or ""
        used_for = item.get("used_for") or "线索"
        viewpoint = item.get("viewpoint_summary") or ""
        rules = item.get("cited_rules_summary") or ""
        detail_parts = []
        if viewpoint:
            detail_parts.append(f"观点：{viewpoint}")
        if rules:
            detail_parts.append(f"规则：{rules}")
        detail = "；".join(detail_parts)
        if url:
            base = f"{title}（{publisher}，{used_for}）：{url}"
        else:
            base = f"{title}（{publisher}，{used_for}）"
        rows.append(base + (f"；{detail}" if detail else ""))
    return "<br>".join(rows) if rows else "无"


def row_from_file(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    meta = data.get("case_metadata") or {}
    source = data.get("source") or {}
    sections = data.get("sections") or {}
    link = source.get("verification_url") or source.get("source_url") or ""
    claims = sections.get("claims") or (data.get("reuse_notes") or {}).get("supports") or ""
    return [
        clean(meta.get("case_name") or sections.get("title") or path.stem),
        clean("；".join(str(x) for x in [meta.get("case_number"), meta.get("court"), meta.get("decision_date")] if x)),
        clean(claims),
        clean(first_excerpt(data)),
        clean(sections.get("judgment_result") or ""),
        clean(link),
        clean(source_materials(data)),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="从案例 JSON 生成 Markdown 案例表")
    parser.add_argument("paths", nargs="+", help="JSON 文件或目录；目录会递归扫描 *.json")
    parser.add_argument("--only-complete", action="store_true", help="只输出 full_text_status=complete 的案例")
    args = parser.parse_args()

    files: list[Path] = []
    for raw in args.paths:
        p = Path(raw)
        files.extend(sorted(p.rglob("*.json")) if p.is_dir() else [p])

    print("| " + " | ".join(HEADERS) + " |")
    print("| " + " | ".join(["---"] * len(HEADERS)) + " |")
    for file in files:
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            if args.only_complete and data.get("full_text_status") != "complete":
                continue
            print("| " + " | ".join(row_from_file(file)) + " |")
        except Exception as exc:
            print("| " + " | ".join([clean(file.name), "读取失败", clean(exc), "", "", "", ""]) + " |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
