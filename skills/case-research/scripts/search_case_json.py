#!/usr/bin/env python3
"""Search local matter case JSON archives."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def flatten(value: Any) -> str:
    if isinstance(value, dict):
        return "\n".join(flatten(v) for v in value.values())
    if isinstance(value, list):
        return "\n".join(flatten(v) for v in value)
    if value is None:
        return ""
    return str(value)


def summarize(data: dict[str, Any], path: Path) -> str:
    meta = data.get("case_metadata") or {}
    source = data.get("source") or {}
    return " | ".join(
        [
            str(meta.get("case_name") or data.get("case_name") or path.stem),
            str(meta.get("case_number") or "案号待确认"),
            str(meta.get("court") or "法院待确认"),
            str(meta.get("decision_date") or "日期待确认"),
            str(data.get("full_text_status") or "status待确认"),
            str(source.get("verification_url") or source.get("source_url") or "无链接"),
            str(path),
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="检索当前事项或指定旧项目中的 case-json")
    parser.add_argument("queries", nargs="+", help="关键词；多词默认 AND 匹配")
    parser.add_argument("--root", action="append", default=[], help="检索根目录，可重复；默认 ./case-json")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--or", dest="match_or", action="store_true", help="关键词 OR 匹配")
    args = parser.parse_args()

    roots = [Path(r).expanduser() for r in args.root] or [Path.cwd() / "case-json"]
    queries = [q.lower() for q in args.queries]

    hits = 0
    for root in roots:
        if not root.exists():
            continue
        for file in sorted(root.rglob("*.json")):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
            except Exception:
                continue
            haystack = (flatten(data) + "\n" + str(file)).lower()
            matched = any(q in haystack for q in queries) if args.match_or else all(q in haystack for q in queries)
            if matched:
                print(summarize(data, file))
                hits += 1
                if hits >= args.limit:
                    return 0
    if hits == 0:
        print("NO_MATCH")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
