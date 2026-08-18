#!/usr/bin/env python3
"""File-based local professional knowledge base bootstrapper and updater."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET


START = "<!-- local-professional-knowledge-base:start -->"
END = "<!-- local-professional-knowledge-base:end -->"
SUPPORTED_TEXT = {".md", ".txt", ".csv", ".json", ".jsonl", ".yaml", ".yml", ".xml", ".html"}
MINERU_SUFFIXES = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".png", ".jpg", ".jpeg", ".webp"}
XLSX_SUFFIXES = {".xlsx"}
SKIP_DIRS = {".git", ".hg", ".svn", "材料镜像", "材料索引", ".automation", "__pycache__"}
RELATION_TYPES = {"revises", "repeals", "cites", "interprets", "applies", "conflicts", "distinguishes", "supplements"}


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_text(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gb18030", "gbk", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def jsonl_load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"{path.name} 第 {line_no} 行不是有效 JSON: {exc}") from exc
    return rows


def jsonl_write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def file_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return "pdf"
    if suffix in MINERU_SUFFIXES - {".pdf"}:
        return "image" if suffix in {".png", ".jpg", ".jpeg", ".webp"} else "office"
    if suffix in XLSX_SUFFIXES:
        return "spreadsheet"
    if suffix in SUPPORTED_TEXT:
        return "text"
    return "other"


def discover_sources(raw_root: Path) -> list[Path]:
    if not raw_root.exists():
        return []
    result = []
    for path in sorted(raw_root.rglob("*")):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(raw_root).parts
        if any(part.startswith(".") or part in SKIP_DIRS for part in rel_parts):
            continue
        result.append(path)
    return result


def material_id(source_rel: str) -> str:
    return "mat-" + hashlib.sha1(source_rel.encode("utf-8")).hexdigest()[:12]


def mirror_rel(source_rel: str) -> str:
    return source_rel + ".md"


def tokenize(text: str) -> list[str]:
    terms = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z][A-Za-z0-9_-]{2,}|\d{2,}", text)
    counts = Counter(term.lower() for term in terms)
    return [term for term, _ in counts.most_common(16)]


def headings(text: str) -> list[str]:
    return [line.lstrip("# ").strip()[:120] for line in text.splitlines() if line.startswith("#")][:12]


def placeholder(source_rel: str, source: Path, reason: str) -> str:
    return "\n".join(
        [
            f"# {source.stem}",
            "",
            "> 此文件当前只有镜像占位信息，不能据此确认原文内容。需要核验时请回看原件。",
            "",
            f"- 原件相对路径：`{source_rel}`",
            f"- 文件类型：`{file_type(source)}`",
            f"- 处理状态：`{reason}`",
            "",
        ]
    )


def write_placeholder(target: Path, source_rel: str, source: Path, reason: str) -> str:
    text = placeholder(source_rel, source, reason)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return text


def xlsx_markdown(source: Path) -> str:
    ns = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    rel_ns = {"rel": "http://schemas.openxmlformats.org/package/2006/relationships"}
    with ZipFile(source) as zf:
        shared = []
        try:
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for item in root.findall("main:si", ns):
                shared.append("".join(node.text or "" for node in item.findall(".//main:t", ns)))
        except KeyError:
            pass
        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        rel_map = {r.attrib.get("Id"): r.attrib.get("Target") for r in rels.findall("rel:Relationship", rel_ns)}
        parts = [f"# {source.stem}"]
        for sheet in workbook.findall("main:sheets/main:sheet", ns):
            name = sheet.attrib.get("name", "Sheet")
            rid = sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            target = rel_map.get(rid)
            if not target:
                continue
            target_path = target if target.startswith("xl/") else "xl/" + target.lstrip("/")
            root = ET.fromstring(zf.read(target_path))
            matrix = []
            max_col = 0
            for row in root.findall(".//main:sheetData/main:row", ns):
                values = {}
                for cell in row.findall("main:c", ns):
                    ref = cell.attrib.get("r", "")
                    letters = "".join(ch for ch in ref if ch.isalpha())
                    col = 0
                    for char in letters.upper():
                        col = col * 26 + ord(char) - 64
                    col = max(0, col - 1)
                    kind = cell.attrib.get("t")
                    value = cell.findtext("main:v", default="", namespaces=ns)
                    if kind == "s" and value.isdigit() and int(value) < len(shared):
                        value = shared[int(value)]
                    elif kind == "inlineStr":
                        value = "".join(node.text or "" for node in cell.findall(".//main:t", ns))
                    values[col] = value.strip()
                    max_col = max(max_col, col + 1)
                if values:
                    matrix.append([values.get(i, "") for i in range(max_col)])
            parts.append(f"\n## {name}")
            if not matrix:
                parts.append("\n（空表）")
                continue
            header = matrix[0]
            data = matrix[1:] if len(matrix) > 1 else []
            if not any(header):
                header = [f"列{i + 1}" for i in range(max_col)]
                data = matrix
            parts.append("\n| " + " | ".join(x.replace("|", "\\|") or " " for x in header) + " |")
            parts.append("| " + " | ".join("---" for _ in header) + " |")
            for row in data:
                parts.append("| " + " | ".join(x.replace("|", "\\|") for x in row) + " |")
    return "\n".join(parts).strip() + "\n"


def find_mineru() -> Path | None:
    candidates = []
    configured = os.environ.get("MINERU_SKILL_PATH")
    if configured:
        candidates.append(Path(configured))
    here = Path(__file__).resolve().parents[1]
    candidates.extend([here.parent / "mineru-ocr", Path.home() / ".codex/skills/mineru-ocr", Path.home() / ".claude/skills/mineru-ocr"])
    for base in [Path.cwd(), *Path.cwd().parents]:
        candidates.extend([base / ".codex/skills/mineru-ocr", base / ".claude/skills/mineru-ocr"])
    for candidate in candidates:
        script = candidate / "scripts/convert.js"
        if script.exists():
            return script
    return None


def run_mineru(source: Path, target: Path, source_rel: str) -> tuple[str, str]:
    script = find_mineru()
    if not script:
        return write_placeholder(target, source_rel, source, "pending: mineru-ocr 未找到"), "pending"
    with tempfile.TemporaryDirectory(prefix="lpkg_ocr_") as temp:
        staged = Path(temp) / source.name
        shutil.copy2(source, staged)
        result = subprocess.run(["/usr/bin/osascript", "-l", "JavaScript", str(script), str(staged)], capture_output=True, text=True)
        staged_md = staged.with_suffix(".md")
        if result.returncode != 0 or not staged_md.exists():
            return write_placeholder(target, source_rel, source, "failed: mineru-ocr 调用失败"), "failed"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(staged_md, target)
        return read_text(target), "success"


def agents_block() -> str:
    return f"""{START}
## 本地专业知识库

本项目采用文件型专业知识库，不采用 Wiki 页面体系。

- 原始材料：`原始材料/`
- Markdown 镜像：`材料镜像/`
- 机器索引：`材料索引/manifest.jsonl`
- 规模摘要：`材料索引/summary.json`
- 人工入口：`材料索引/材料地图.md`
- 原件映射：`材料索引/source-map.jsonl`
- 已确认关系：`材料索引/relations.jsonl`
- 增量比较队列：`材料索引/待比较.jsonl`

### 更新规则

- 用户维护原件；Agent 不修改、移动、重命名、删除或覆盖原件。
- 用户要求“更新知识库”时，调用 `local-professional-knowledge-base` 做一次增量更新，不启动后台监控。
- 文本文件直接生成镜像；PDF、扫描件、图片和复杂 Office 文件路由到已安装的 `mineru-ocr`。
- MinerU Token 只能保存在本机 Skill 配置中，不得写入项目、索引、日志或答复。
- 新增或变更材料处理后，检查待比较队列；只有实际阅读比较后，才记录修订、废止、引用、解释、冲突、区分或补充关系。

### 检索规则

- 先读 `材料索引/材料地图.md` 和 `manifest.jsonl`，再在 `材料镜像/` 中按关键词定位；不得默认一次性读取全部镜像。
- Markdown 是检索镜像，不是自动确认的专业结论。
- 回答尽量给出镜像路径、原件路径和可获得的页码或章节。
- OCR 失败、质量可疑、来源不明或关系未确认时，明确标记并回看原件。
{END}
"""


def update_agents(project: Path) -> None:
    path = project / "AGENTS.md"
    block = agents_block()
    if not path.exists():
        path.write_text("# 项目级 AGENTS.md\n\n" + block, encoding="utf-8")
        return
    text = read_text(path)
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END) + r"\n?", re.S)
    text = pattern.sub(block, text) if pattern.search(text) else text.rstrip() + "\n\n" + block
    path.write_text(text, encoding="utf-8")


def init(project: Path) -> None:
    project.mkdir(parents=True, exist_ok=True)
    (project / "原始材料").mkdir(exist_ok=True)
    (project / "材料镜像").mkdir(exist_ok=True)
    index = project / "材料索引"
    index.mkdir(exist_ok=True)
    update_agents(project)
    for name in ("manifest.jsonl", "source-map.jsonl", "relations.jsonl", "待比较.jsonl"):
        (index / name).touch(exist_ok=True)
    if not (index / "summary.json").exists():
        (index / "summary.json").write_text(json.dumps({"total_files": 0, "active_files": 0}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not (index / "材料地图.md").exists():
        (index / "材料地图.md").write_text("# 材料地图\n\n尚未扫描原始材料。把法规、案例、文章、书籍或其他专业材料放入 `原始材料/` 后运行一次增量更新。\n", encoding="utf-8")
    print(f"已初始化本地专业知识库：{project}")


def load_previous(index: Path) -> tuple[list[dict], dict[str, dict]]:
    rows = jsonl_load(index / "manifest.jsonl")
    by_path = {}
    for row in rows:
        source_path = str(row.get("source_path") or "")
        if source_path.startswith("原始材料/"):
            source_path = source_path[len("原始材料/"):]
        if source_path:
            by_path[source_path] = row
    return rows, by_path


def find_reuse(old_rows: list[dict], source_rel: str, digest: str) -> dict | None:
    for row in old_rows:
        if row.get("sha256") == digest and row.get("processing_status") != "removed":
            return row
    return None


def candidate_queue(changed: list[dict], active: list[dict]) -> list[dict]:
    queue = []
    for row in changed:
        source_terms = set(row.get("keywords") or [])
        title_terms = set(tokenize(row.get("title", "")))
        candidates = []
        for other in active:
            if other["material_id"] == row["material_id"]:
                continue
            other_terms = set(other.get("keywords") or []) | set(tokenize(other.get("title", "")))
            score = len((source_terms | title_terms) & other_terms)
            if score:
                candidates.append((score, other["material_id"]))
        candidates.sort(reverse=True)
        queue.append({
            "material_id": row["material_id"],
            "change_type": row.get("change_type", "modified"),
            "candidate_material_ids": [item[1] for item in candidates[:12]],
            "candidate_scores": {item[1]: item[0] for item in candidates[:12]},
            "reason": "新增或内容变化后按标题/词项召回候选旧材料；需 Agent 阅读确认关系。",
            "created_at": now(),
        })
    return queue


def build_map(project: Path, rows: list[dict], summary: dict) -> None:
    lines = ["# 材料地图", "", "> 这是材料入口和检索地图，不是 Wiki 页面，也不是专业结论汇编。", "", f"- 更新时间：{summary['updated_at']}", f"- 在库材料：{summary['active_files']}", f"- 已移除材料：{summary['removed_files']}", f"- 待比较材料：{summary['pending_comparisons']}", f"- 已确认/记录关系：{summary['relations']}", "", "## 按材料状态", "", "| 状态 | 数量 |", "|---|---:|"]
    for key, value in sorted(summary["status_counts"].items()):
        lines.append(f"| {key} | {value} |")
    lines.extend(["", "## 材料入口", "", "| 材料 ID | 标题 | 原件 | Markdown 镜像 | 处理方式 | 状态 |", "|---|---|---|---|---|---|"])
    for row in rows:
        if row.get("processing_status") == "removed":
            continue
        lines.append(f"| `{row['material_id']}` | {row['title']} | `{row['source_path']}` | `{row['mirror_path']}` | `{row['ingest_mode']}` | `{row['processing_status']}` |")
    (project / "材料索引/材料地图.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def update(project: Path, process: bool, force: bool) -> None:
    raw = project / "原始材料"
    index = project / "材料索引"
    if not raw.exists():
        raise RuntimeError("缺少 原始材料/；先运行 init")
    index.mkdir(exist_ok=True)
    old_rows, old_by_path = load_previous(index)
    old_by_id = {row.get("material_id"): row for row in old_rows}
    sources = discover_sources(raw)
    seen = set()
    rows = []
    changed = []
    stats = Counter()
    for source in sources:
        rel = source.relative_to(raw).as_posix()
        digest = sha256(source)
        previous = old_by_path.get(rel) or find_reuse(old_rows, rel, digest)
        mat_id = str(previous.get("material_id")) if previous else material_id(rel)
        target_rel = mirror_rel(rel)
        target = project / "材料镜像" / target_rel
        same = previous and previous.get("sha256") == digest and target.exists() and not force
        if same:
            row = dict(previous)
            row["source_path"] = f"原始材料/{rel}"
            row["mirror_path"] = f"材料镜像/{target_rel}"
            row["change_type"] = "unchanged"
            seen.add(mat_id)
            rows.append(row)
            stats["unchanged"] += 1
            continue
        if previous and previous.get("source_path") != f"原始材料/{rel}":
            stats["renamed"] += 1
        elif previous:
            stats["modified"] += 1
        else:
            stats["added"] += 1
        if previous and previous.get("mirror_path") != f"材料镜像/{target_rel}":
            old_target = project / str(previous["mirror_path"])
            if old_target.exists() and old_target != target:
                old_target.unlink()
        text = ""
        mode = "pending"
        status = "pending"
        if source.suffix.lower() in SUPPORTED_TEXT:
            text = read_text(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
            mode = "text_copy"
            status = "success"
        elif source.suffix.lower() in XLSX_SUFFIXES and process:
            try:
                text = xlsx_markdown(source)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding="utf-8")
                mode = "xlsx_native"
                status = "success"
            except Exception:
                text = write_placeholder(target, f"原始材料/{rel}", source, "failed: XLSX 解析失败")
                mode = "placeholder"
                status = "failed"
        elif source.suffix.lower() in MINERU_SUFFIXES and process:
            text, status = run_mineru(source, target, f"原始材料/{rel}")
            mode = "mineru" if status == "success" else "placeholder"
        else:
            text = write_placeholder(target, f"原始材料/{rel}", source, "pending: 等待处理")
            mode = "pending"
            status = "pending"
        row = {
            "material_id": mat_id,
            "title": source.stem,
            "source_path": f"原始材料/{rel}",
            "mirror_path": f"材料镜像/{target_rel}",
            "sha256": digest,
            "mirror_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest() if text else "",
            "file_type": file_type(source),
            "ingest_mode": mode,
            "processing_status": status,
            "ocr_quality": "not_applicable" if source.suffix.lower() in SUPPORTED_TEXT or source.suffix.lower() in XLSX_SUFFIXES else ("unreviewed" if status == "success" else "failed"),
            "keywords": tokenize(source.stem + "\n" + text[:12000]),
            "headings": headings(text),
            "change_type": "modified" if previous else "added",
            "updated_at": now(),
        }
        seen.add(mat_id)
        rows.append(row)
        changed.append(row)
        stats[status] += 1
    for old in old_rows:
        if old.get("material_id") in seen or old.get("processing_status") == "removed":
            if old.get("processing_status") == "removed" and old.get("material_id") not in seen:
                rows.append(old)
            continue
        removed = dict(old)
        removed["processing_status"] = "removed"
        removed["change_type"] = "removed"
        removed["updated_at"] = now()
        rows.append(removed)
        old_target = project / str(old.get("mirror_path", ""))
        if old_target.exists():
            old_target.unlink()
        stats["removed"] += 1
    rows.sort(key=lambda row: (row.get("processing_status") == "removed", row.get("source_path", "")))
    jsonl_write(index / "manifest.jsonl", rows)
    jsonl_write(index / "source-map.jsonl", [{key: row.get(key, "") for key in ("material_id", "source_path", "mirror_path", "sha256", "processing_status")} for row in rows])
    active = [row for row in rows if row.get("processing_status") != "removed"]
    relations = jsonl_load(index / "relations.jsonl")
    queue = candidate_queue(changed, active)
    jsonl_write(index / "待比较.jsonl", queue)
    summary = {
        "updated_at": now(),
        "total_files": len(rows),
        "active_files": len(active),
        "removed_files": len(rows) - len(active),
        "status_counts": dict(Counter(str(row.get("processing_status")) for row in rows)),
        "file_type_counts": dict(Counter(str(row.get("file_type")) for row in active)),
        "ingest_mode_counts": dict(Counter(str(row.get("ingest_mode")) for row in active)),
        "pending_comparisons": len(queue),
        "relations": len(relations),
    }
    (index / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    build_map(project, rows, summary)
    (index / "本次更新.json").write_text(json.dumps({"updated_at": summary["updated_at"], "stats": dict(stats), "pending_comparisons": len(queue)}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"project": str(project), "stats": dict(stats), "pending_comparisons": len(queue)}, ensure_ascii=False, indent=2))


def validate(project: Path) -> int:
    index = project / "材料索引"
    errors = []
    for directory in (project / "原始材料", project / "材料镜像", index):
        if not directory.exists():
            errors.append(f"缺少目录: {directory.name}")
    try:
        rows = jsonl_load(index / "manifest.jsonl")
        jsonl_load(index / "source-map.jsonl")
        jsonl_load(index / "relations.jsonl")
        jsonl_load(index / "待比较.jsonl")
        json.loads((index / "summary.json").read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(str(exc))
        rows = []
    ids = {row.get("material_id") for row in rows}
    for row in rows:
        if row.get("processing_status") == "removed":
            continue
        source = project / str(row.get("source_path", ""))
        mirror = project / str(row.get("mirror_path", ""))
        if not source.exists():
            errors.append(f"原件不存在: {row.get('source_path')}")
        if not mirror.exists():
            errors.append(f"镜像不存在: {row.get('mirror_path')}")
    for relation in jsonl_load(index / "relations.jsonl"):
        if relation.get("from_material_id") not in ids or relation.get("to_material_id") not in ids:
            errors.append(f"关系引用未知材料: {relation.get('relation_id', '')}")
        if relation.get("relation_type") not in RELATION_TYPES:
            errors.append(f"未知关系类型: {relation.get('relation_type', '')}")
    if errors:
        print("校验失败：")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(f"校验通过：{len(rows)} 条材料记录；原件、镜像、索引和关系引用均可对应。")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="本地专业知识库：初始化、增量更新与校验")
    sub = parser.add_subparsers(dest="command", required=True)
    p_init = sub.add_parser("init")
    p_init.add_argument("project")
    p_update = sub.add_parser("update")
    p_update.add_argument("project")
    p_update.add_argument("--process", action="store_true", help="处理 XLSX，并把 PDF/Office/图片路由到 MinerU")
    p_update.add_argument("--force", action="store_true")
    p_validate = sub.add_parser("validate")
    p_validate.add_argument("project")
    args = parser.parse_args()
    project = Path(args.project).expanduser().resolve()
    if args.command == "init":
        init(project)
        return 0
    if args.command == "update":
        update(project, args.process, args.force)
        return 0
    return validate(project)


if __name__ == "__main__":
    raise SystemExit(main())
