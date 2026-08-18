#!/usr/bin/env python3
"""Read-only structural audit for a client Wiki.

The script reports deterministic file-system and link issues. It does not
rewrite pages or evaluate the substance of legal conclusions.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


CORE_FILES = ("规则.md", "索引.md", "日志.md", "原材料地图.md")
WIKI_LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
MD_LINK_RE = re.compile(r"!?(?:\[[^\]]*\])\(([^)]+)\)")
ABSOLUTE_PATH_RE = re.compile(r"/(?:Users|Volumes|private/var|tmp)/[^\s`)'\"]+")
SECRET_RE = re.compile(r"(?i)(?:bearer\s+[A-Za-z0-9._-]{12,}|sk-[A-Za-z0-9_-]{16,}|token\s*[:=]\s*['\"]?[A-Za-z0-9._-]{16,})")
CURRENT_RE = re.compile(r"(?i)(当前|现行|目前|应当|不得|必须|统一要求|固定口径)")


def rel_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def target_to_path(raw: str, source: Path, root: Path, *, wiki_link: bool = False) -> Path | None:
    target = raw.strip().split("#", 1)[0].strip()
    if not target or target.startswith(("http://", "https://", "mailto:", "data:")):
        return None
    target_path = Path(target)
    if target_path.is_absolute():
        return target_path
    if wiki_link and target_path.suffix.lower() != ".md":
        target_path = target_path.with_suffix(".md")
    if wiki_link:
        # Existing pages use three forms: root-style [[目录/页面]], relative
        # [[../目录/页面]], and same-folder [[页面]]. Prefer a same-folder
        # match for a bare page name, then fall back to the Wiki root.
        if target.startswith(("./", "../")):
            return (source.parent / target_path).resolve()
        if "/" not in target and (source.parent / target_path).exists():
            return (source.parent / target_path).resolve()
        return (root / target_path).resolve()
    # Markdown links, including images, resolve from the current page and keep
    # their original extension. Only extensionless links get the usual .md
    # fallback.
    if target_path.suffix == "":
        target_path = target_path.with_suffix(".md")
    return source.parent / target_path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def add_issue(issues: list[dict[str, str]], level: str, code: str, message: str, path: str = "") -> None:
    item = {"level": level, "code": code, "message": message}
    if path:
        item["path"] = path
    issues.append(item)


def audit(root: Path) -> dict[str, Any]:
    root = root.resolve()
    issues: list[dict[str, str]] = []
    if not root.is_dir():
        return {
            "root": str(root),
            "summary": {"errors": 1, "warnings": 0},
            "issues": [{"level": "error", "code": "missing-root", "message": "Wiki directory does not exist"}],
        }

    pages = sorted(root.rglob("*.md"))
    page_set = set(pages)
    for name in CORE_FILES:
        if not (root / name).is_file():
            add_issue(issues, "error", "missing-core", f"Missing required file: {name}", name)

    title_paths: dict[str, list[str]] = {}
    indexed_targets: set[Path] = set()
    for page in pages:
        rel = rel_posix(page, root)
        text = read_text(page)
        headings = re.findall(r"^#\s+(.+?)\s*$", text, flags=re.MULTILINE)
        title = headings[0].strip() if headings else page.stem
        title_paths.setdefault(title, []).append(rel)

        if ABSOLUTE_PATH_RE.search(text):
            add_issue(issues, "warning", "absolute-path", "Page contains an absolute local path", rel)
        if SECRET_RE.search(text):
            add_issue(issues, "error", "secret-like-text", "Page contains text matching a token-like pattern", rel)
        if page.name not in CORE_FILES and CURRENT_RE.search(text) and not re.search(r"(?i)(来源|依据|source|confirmed_at|确认时间|待核验|历史)", text):
            add_issue(issues, "warning", "current-without-source-marker", "Page appears to state current rules without an obvious source/status marker", rel)

        if page.name == "索引.md":
            for raw in WIKI_LINK_RE.findall(text):
                target = target_to_path(raw, page, root, wiki_link=True)
                if target:
                    indexed_targets.add(target.resolve())

        for raw in WIKI_LINK_RE.findall(text):
            target = target_to_path(raw, page, root, wiki_link=True)
            if target and target not in page_set and not target.exists():
                add_issue(issues, "error", "broken-wiki-link", f"Broken Wiki link: {raw}", rel)
        for raw in MD_LINK_RE.findall(text):
            target = target_to_path(raw, page, root)
            if target and target.is_relative_to(root) and target not in page_set and not target.exists():
                add_issue(issues, "error", "broken-md-link", f"Broken Markdown link: {raw}", rel)

    for title, paths in title_paths.items():
        if len(paths) > 1:
            add_issue(issues, "warning", "duplicate-title", f"Duplicate page title: {title} ({', '.join(paths)})")

    for page in pages:
        rel = rel_posix(page, root)
        if rel in CORE_FILES or page.name.startswith("文件清单"):
            continue
        if page.resolve() not in indexed_targets:
            add_issue(issues, "warning", "unindexed-page", "Markdown page is not linked from 索引.md", rel)

    counts = Counter(item["level"] for item in issues)
    return {
        "root": str(root),
        "pages": len(pages),
        "summary": {"errors": counts.get("error", 0), "warnings": counts.get("warning", 0)},
        "issues": issues,
    }


def markdown_report(result: dict[str, Any]) -> str:
    lines = [
        "# 客户 Wiki 结构审计报告",
        "",
        f"- 路径：`{result['root']}`",
        f"- Markdown 页面：{result.get('pages', 0)}",
        f"- 错误：{result['summary']['errors']}",
        f"- 警告：{result['summary']['warnings']}",
        "",
    ]
    if not result["issues"]:
        lines.append("未发现结构问题。")
        return "\n".join(lines) + "\n"
    lines.extend(["## 问题", "", "| 级别 | 代码 | 文件 | 说明 |", "|---|---|---|---|"])
    for item in result["issues"]:
        lines.append(f"| {item['level']} | `{item['code']}` | `{item.get('path', '')}` | {item['message']} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit a client Wiki without modifying it")
    parser.add_argument("command", choices=("check", "report"))
    parser.add_argument("wiki", type=Path)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args()
    result = audit(args.wiki)
    if args.command == "check":
        print(json.dumps(result["summary"], ensure_ascii=False, sort_keys=True))
        for item in result["issues"]:
            print(f"{item['level']}: {item['code']}: {item.get('path', '')} {item['message']}")
        return 1 if result["summary"]["errors"] else 0
    if args.format == "markdown":
        print(markdown_report(result), end="")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
