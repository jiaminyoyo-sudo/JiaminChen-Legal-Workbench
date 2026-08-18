#!/usr/bin/env python3
"""Utilities for matter-local case archives."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


def safe_name(value: str) -> str:
    value = re.sub(r"[\\/:*?\"<>|]+", "_", value.strip())
    value = re.sub(r"\s+", "_", value)
    return value[:80] or "事项"


def cmd_init(args: argparse.Namespace) -> int:
    date = args.date or datetime.now().strftime("%Y-%m-%d")
    root = Path(args.matter_root).expanduser().resolve()
    archive = root / "case-json" / f"{date}_{safe_name(args.matter_name)}"
    archive.mkdir(parents=True, exist_ok=True)
    print(archive)
    return 0


def cmd_stamp(args: argparse.Namespace) -> int:
    path = Path(args.json_path)
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    sections = data.setdefault("sections", {})
    full_text = sections.get("full_text") or ""
    integrity = data.setdefault("integrity", {})
    integrity["full_text_char_count"] = len(full_text)
    integrity["sha256"] = hashlib.sha256(full_text.encode("utf-8")).hexdigest() if full_text else ""
    integrity["has_court_reasoning"] = bool(sections.get("court_reasoning"))
    integrity["has_judgment_result"] = bool(sections.get("judgment_result"))
    integrity["checked_complete"] = data.get("full_text_status") == "complete" and bool(full_text)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(path)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="事项内案例归档辅助工具")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="创建事项内 case-json 日期目录")
    p_init.add_argument("--matter-root", default=".", help="当前事项最底层目录，默认当前目录")
    p_init.add_argument("--matter-name", required=True, help="事项名")
    p_init.add_argument("--date", help="YYYY-MM-DD；默认今天")
    p_init.set_defaults(func=cmd_init)

    p_stamp = sub.add_parser("stamp", help="回填 integrity.full_text_char_count/sha256 等字段")
    p_stamp.add_argument("json_path")
    p_stamp.set_defaults(func=cmd_stamp)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
