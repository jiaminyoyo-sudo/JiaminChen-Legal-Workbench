#!/usr/bin/env python3
"""Merge a Pkulaw-downloaded judgment TXT into a case-research JSON archive."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from typing import Any


def now_cst() -> str:
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(timespec="seconds")


def read_text(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    raw = re.sub(r"\n{3,}", "\n\n", raw)
    return raw.strip()


def extract_between(text: str, start_patterns: list[str], end_patterns: list[str]) -> str:
    start = -1
    for pat in start_patterns:
        m = re.search(pat, text)
        if m:
            start = m.start()
            break
    if start < 0:
        return ""

    tail = text[start:]
    end_positions: list[int] = []
    for pat in end_patterns:
        m = re.search(pat, tail)
        if m and m.start() > 20:
            end_positions.append(m.start())
    end = min(end_positions) if end_positions else len(tail)
    return tail[:end].strip()


def extract_reasoning(text: str) -> str:
    return extract_between(
        text,
        [r"本院认为[，,:：]", r"本院经审查认为[，,:：]", r"本院认为"],
        [r"综上[，,:：]", r"依照.+判决如下", r"判决如下[：:]", r"裁定如下[：:]", r"审判长", r"二〇"],
    )


def extract_result(text: str) -> str:
    result = extract_between(
        text,
        [r"判决如下[：:]", r"裁定如下[：:]"],
        [r"如不服本判决", r"如不服本裁定", r"审判长", r"二〇", r"本判决为终审判决"],
    )
    if result:
        return result
    tail = text[-1500:]
    m = re.search(r"(驳回.+?请求|维持原判|撤销.+?判决|准许.+?撤诉|本判决为终审判决)", tail, re.S)
    return m.group(0).strip() if m else ""


def load_seed(path: Path | None) -> dict[str, Any]:
    if not path:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_dict(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        value = {}
        data[key] = value
    return value


def merge_txt(seed: dict[str, Any], txt: str, source_url: str, access_method: str) -> dict[str, Any]:
    data = dict(seed)
    data.setdefault("archive_version", "1.0")
    data["retrieved_at"] = data.get("retrieved_at") or now_cst()
    data.setdefault("retrieved_by", "大成律师")

    source = ensure_dict(data, "source")
    source.setdefault("database", "北大法宝")
    if source_url:
        source["source_url"] = source_url
        source["verification_url"] = source.get("verification_url") or source_url
    source["access_method"] = access_method

    sections = ensure_dict(data, "sections")
    sections["full_text"] = txt
    sections.setdefault("title", txt.split("\n", 1)[0].strip() if txt else "")
    reasoning = extract_reasoning(txt)
    result = extract_result(txt)
    if reasoning:
        sections["court_reasoning"] = reasoning
    if result:
        sections["judgment_result"] = result

    data["full_text_status"] = "complete" if len(txt) >= 3000 and reasoning and result else "partial"
    if data["full_text_status"] == "complete":
        data["not_complete_reason"] = ""
        data["next_retrieval_steps"] = ""
    else:
        data["not_complete_reason"] = data.get("not_complete_reason") or "已导入 txt，但脚本未能确认全文完整或未切出本院认为/裁判结果。"
        data["next_retrieval_steps"] = data.get("next_retrieval_steps") or "人工核对 txt 是否完整，并补齐 sections.court_reasoning、sections.judgment_result。"

    if reasoning and not data.get("excerpts"):
        data["excerpts"] = [{
            "purpose": "与检索问题相关的法院说理",
            "quote": reasoning[:1800],
            "section": "court_reasoning",
        }]

    integrity = ensure_dict(data, "integrity")
    integrity["full_text_char_count"] = len(txt)
    integrity["sha256"] = hashlib.sha256(txt.encode("utf-8")).hexdigest()
    integrity["has_court_reasoning"] = bool(sections.get("court_reasoning"))
    integrity["has_judgment_result"] = bool(sections.get("judgment_result"))
    integrity["checked_complete"] = data["full_text_status"] == "complete"
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="把法宝下载/复制的裁判文书 txt 合并进案例 JSON")
    parser.add_argument("txt", help="法宝下载或复制得到的 txt 文件")
    parser.add_argument("-s", "--seed-json", help="既有线索 JSON，可选")
    parser.add_argument("-o", "--output", required=True, help="输出 JSON 路径")
    parser.add_argument("--source-url", default="", help="法宝案例链接")
    parser.add_argument("--access-method", default="法宝详情页 txt 下载", help="全文获取方式")
    args = parser.parse_args()

    txt = read_text(Path(args.txt))
    seed = load_seed(Path(args.seed_json)) if args.seed_json else {}
    data = merge_txt(seed, txt, args.source_url, args.access_method)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out)
    print(f"full_text_status={data.get('full_text_status')} chars={len(txt)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
