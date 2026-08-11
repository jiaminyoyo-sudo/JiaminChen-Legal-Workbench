#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
针对合同修订中的小粒度修改，写入 Word 原生修订标记。

适用场景：
- 替换数字、期限、名称
- 删除局部过重表述
- 在锚点前后补一句短语或短句

不替代原 skill 的完整审查逻辑，只是把“精准修改”这一层做稳。

Contract 4 增加操作范围闸门：
- 默认拒绝大段删除、替换或插入；
- 确需结构性修订时，必须逐项声明 allow_broad_change 并说明 reason；
- 可先用 --check-only 校验锚点和修改范围，不写入文件。
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import shutil
import tempfile
import zipfile
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from lxml import etree

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NSMAP = {"w": W_NS}
MAX_LOCAL_CHANGE_CHARS = 80
MAX_LOCAL_SENTENCE_BREAKS = 1
SENTENCE_BREAK_RE = re.compile(r"[。！？!?；;\n]")


def w_tag(name: str) -> str:
    return f"{{{W_NS}}}{name}"


@dataclass
class RunSlice:
    element: etree._Element
    text: str
    start: int
    end: int


class PreciseRevisionError(Exception):
    pass


def narrow_replace_window(original: str, replacement: str) -> tuple[int, int, int, int]:
    """返回真正变化窗口在原文和替换文本中的起止位置。"""
    prefix_len = 0
    max_prefix = min(len(original), len(replacement))
    while prefix_len < max_prefix and original[prefix_len] == replacement[prefix_len]:
        prefix_len += 1

    original_suffix = len(original)
    replacement_suffix = len(replacement)
    while (
        original_suffix > prefix_len
        and replacement_suffix > prefix_len
        and original[original_suffix - 1] == replacement[replacement_suffix - 1]
    ):
        original_suffix -= 1
        replacement_suffix -= 1

    return prefix_len, original_suffix, prefix_len, replacement_suffix


def changed_texts(op: dict) -> tuple[str, str]:
    """提取操作真正删除和新增的文本，用于审计可见修订范围。"""
    op_type = op["type"]
    if op_type == "replace":
        original = op.get("target", "")
        replacement = op.get("replacement", "")
        old_start, old_end, new_start, new_end = narrow_replace_window(original, replacement)
        return original[old_start:old_end], replacement[new_start:new_end]
    if op_type == "delete":
        return op.get("target", ""), ""
    return "", op.get("text", "")


def validate_operation_scope(op: dict, index: int) -> str | None:
    """
    默认只允许字词、短语和单个短句层面的可见修订。

    返回结构性修订说明；局部修订返回 None。
    """
    deleted, inserted = changed_texts(op)
    footprint = max(len(deleted), len(inserted))
    sentence_breaks = max(
        len(SENTENCE_BREAK_RE.findall(deleted)),
        len(SENTENCE_BREAK_RE.findall(inserted)),
    )
    is_broad = footprint > MAX_LOCAL_CHANGE_CHARS or sentence_breaks > MAX_LOCAL_SENTENCE_BREAKS
    if not is_broad:
        return None

    allowed = op.get("allow_broad_change") is True
    reason = str(op.get("reason", "")).strip()
    if not allowed:
        raise PreciseRevisionError(
            f"第 {index} 个操作可见修改范围过大"
            f"（删除 {len(deleted)} 字，新增 {len(inserted)} 字，句界 {sentence_breaks} 个）。"
            "请拆分为更小操作；确实无法局部修复时，设置 "
            'allow_broad_change: true 并填写具体 reason。'
        )
    if len(reason) < 6:
        raise PreciseRevisionError(
            f"第 {index} 个结构性修订缺少具体理由；reason 至少应说明为何不能局部修复"
        )
    return reason


def validate_operations_scope(operations: list[dict]) -> list[tuple[int, str]]:
    broad_changes: list[tuple[int, str]] = []
    for index, op in enumerate(operations, start=1):
        reason = validate_operation_scope(op, index)
        if reason is not None:
            broad_changes.append((index, reason))
    return broad_changes


def unzip_docx(docx_path: Path, temp_dir: Path) -> None:
    with zipfile.ZipFile(docx_path, "r") as zf:
        zf.extractall(temp_dir)


def zip_docx(temp_dir: Path, output_path: Path) -> None:
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(temp_dir.rglob("*")):
            if file_path.is_file():
                zf.write(file_path, file_path.relative_to(temp_dir))


def validate_docx_package(docx_path: Path) -> None:
    """执行轻量结构校验，不做逐页渲染。"""
    required = {"[Content_Types].xml", "word/document.xml"}
    try:
        with zipfile.ZipFile(docx_path, "r") as zf:
            names = set(zf.namelist())
            missing = required - names
            if missing:
                raise PreciseRevisionError(f"DOCX 缺少必要部件: {', '.join(sorted(missing))}")
            bad_member = zf.testzip()
            if bad_member:
                raise PreciseRevisionError(f"DOCX 压缩包损坏: {bad_member}")
            for name in names:
                if name.endswith(".xml"):
                    etree.fromstring(zf.read(name))
    except (zipfile.BadZipFile, etree.XMLSyntaxError) as exc:
        raise PreciseRevisionError(f"DOCX 结构校验失败: {exc}") from exc


def iter_xml_paths(root_dir: Path) -> list[Path]:
    word_dir = root_dir / "word"
    paths = [word_dir / "document.xml"]
    paths.extend(sorted(word_dir.glob("header*.xml")))
    paths.extend(sorted(word_dir.glob("footer*.xml")))
    return [path for path in paths if path.exists()]


def parse_local_time(raw: str | None) -> datetime:
    if not raw:
        return datetime.now(timezone(timedelta(hours=8))).replace(microsecond=0)
    value = datetime.fromisoformat(raw)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone(timedelta(hours=8)))
    return value.replace(microsecond=0)


def derive_output_path(docx_path: Path, revision_time: datetime) -> Path:
    """默认保留原件，并避免覆盖已存在的修订稿。"""
    date_suffix = revision_time.strftime("%Y%m%d")
    stem = re.sub(r"_DC_修订稿\d{8}(?:_v\d+)?$", "", docx_path.stem)
    candidate = docx_path.with_name(f"{stem}_DC_修订稿{date_suffix}{docx_path.suffix}")
    if not candidate.exists() and candidate != docx_path:
        return candidate
    version = 2
    while True:
        candidate = docx_path.with_name(f"{stem}_DC_修订稿{date_suffix}_v{version}{docx_path.suffix}")
        if not candidate.exists() and candidate != docx_path:
            return candidate
        version += 1


def clone_rpr(run: etree._Element) -> etree._Element | None:
    rpr = run.find("w:rPr", NSMAP)
    if rpr is None:
        return None
    cloned = deepcopy(rpr)
    for color in cloned.findall("w:color", NSMAP):
        cloned.remove(color)
    return cloned


def make_text_node(tag_name: str, text: str) -> etree._Element:
    node = etree.Element(w_tag(tag_name))
    if text[:1].isspace() or text[-1:].isspace():
        node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    node.text = text
    return node


def make_run_like(src_run: etree._Element, text: str) -> etree._Element | None:
    if not text:
        return None
    new_run = etree.Element(w_tag("r"))
    rpr = clone_rpr(src_run)
    if rpr is not None:
        new_run.append(rpr)
    new_run.append(make_text_node("t", text))
    return new_run


def make_revision(
    kind: str,
    revision_id: int,
    author: str,
    revision_date: str,
    text: str,
    src_run: etree._Element,
) -> etree._Element | None:
    if not text:
        return None
    wrapper = etree.Element(w_tag(kind))
    wrapper.set(w_tag("id"), str(revision_id))
    wrapper.set(w_tag("author"), author)
    wrapper.set(w_tag("date"), revision_date)

    run = etree.Element(w_tag("r"))
    rpr = clone_rpr(src_run)
    if rpr is not None:
        run.append(rpr)
    run.append(make_text_node("t" if kind == "ins" else "delText", text))
    wrapper.append(run)
    return wrapper


def paragraph_text_and_runs(paragraph: etree._Element) -> tuple[str, list[RunSlice]]:
    pieces: list[str] = []
    slices: list[RunSlice] = []
    pos = 0
    for child in paragraph:
        if child.tag != w_tag("r"):
            continue
        run_pieces: list[str] = []
        for node in child:
            if node.tag == w_tag("t"):
                run_pieces.append(node.text or "")
            elif node.tag == w_tag("tab"):
                run_pieces.append("\t")
        run_text = "".join(run_pieces)
        if not run_text:
            continue
        end = pos + len(run_text)
        pieces.append(run_text)
        slices.append(RunSlice(child, run_text, pos, end))
        pos = end
    return "".join(pieces), slices


def find_next_revision_id(trees: list[etree._ElementTree]) -> int:
    max_id = 0
    for tree in trees:
        for node in tree.findall(".//w:ins", NSMAP) + tree.findall(".//w:del", NSMAP):
            raw = node.get(w_tag("id"))
            if raw and raw.isdigit():
                max_id = max(max_id, int(raw))
    return max_id + 1


class RevisionApplier:
    def __init__(self, trees: list[etree._ElementTree], author: str, start_time: datetime, interval_minutes: float):
        self.trees = trees
        self.author = author
        self.next_id = find_next_revision_id(trees)
        self.next_time = start_time
        self.interval = timedelta(minutes=interval_minutes)
        self.summary: list[str] = []

    def take_id(self) -> int:
        current = self.next_id
        self.next_id += 1
        return current

    def take_date(self) -> str:
        current = self.next_time
        self.next_time = self.next_time + self.interval
        return current.isoformat()

    def find_match(self, op: dict) -> tuple[etree._Element, int, int, str]:
        key = "anchor" if op["type"] in {"insert_before", "insert_after"} else "target"
        needle = op[key]
        hint = op.get("paragraph_hint")
        occurrence = int(op.get("occurrence", 1))

        def collect(require_hint: bool) -> list[tuple[etree._Element, int, int, str]]:
            matches: list[tuple[etree._Element, int, int, str]] = []
            for tree in self.trees:
                for para in tree.findall(".//w:p", NSMAP):
                    text, _ = paragraph_text_and_runs(para)
                    if not text:
                        continue
                    if require_hint and hint and hint not in text:
                        continue
                    cursor = 0
                    while True:
                        idx = text.find(needle, cursor)
                        if idx == -1:
                            break
                        matches.append((para, idx, idx + len(needle), text))
                        cursor = idx + len(needle)
            return matches

        matches = collect(True)
        if not matches and hint:
            fallback = collect(False)
            if len(fallback) == 1:
                matches = fallback
            elif fallback:
                scored = sorted(
                    (difflib.SequenceMatcher(None, hint, item[3]).ratio(), item)
                    for item in fallback
                )
                best_score, best_item = scored[-1]
                second_score = scored[-2][0] if len(scored) > 1 else 0.0
                if best_score >= 0.6 and best_score - second_score >= 0.05:
                    matches = [best_item]

        if not matches:
            raise PreciseRevisionError(f"未找到目标文本: {needle!r}")
        if occurrence > len(matches):
            raise PreciseRevisionError(f"目标文本 {needle!r} 仅匹配到 {len(matches)} 处，occurrence={occurrence} 超出范围")
        return matches[occurrence - 1]

    @staticmethod
    def insert_nodes_before(anchor: etree._Element, nodes: list[etree._Element]) -> None:
        if not nodes:
            return
        anchor.addprevious(nodes[0])
        prev = nodes[0]
        for node in nodes[1:]:
            prev.addnext(node)
            prev = node

    def replace_span(self, paragraph: etree._Element, start: int, end: int, replacement: str | None) -> None:
        para_text, runs = paragraph_text_and_runs(paragraph)
        affected = [run for run in runs if not (run.end <= start or run.start >= end)]
        if not affected:
            raise PreciseRevisionError("目标文本没有落到可编辑 run 上")

        first = affected[0]
        last = affected[-1]
        prefix = first.text[: max(0, start - first.start)]
        suffix = last.text[max(0, end - last.start) :]
        matched = para_text[start:end]

        new_nodes: list[etree._Element] = []
        prefix_run = make_run_like(first.element, prefix)
        if prefix_run is not None:
            new_nodes.append(prefix_run)

        del_node = make_revision("del", self.take_id(), self.author, self.take_date(), matched, first.element)
        if del_node is not None:
            new_nodes.append(del_node)

        if replacement:
            ins_node = make_revision("ins", self.take_id(), self.author, self.take_date(), replacement, first.element)
            if ins_node is not None:
                new_nodes.append(ins_node)

        suffix_run = make_run_like(last.element, suffix)
        if suffix_run is not None:
            new_nodes.append(suffix_run)

        self.insert_nodes_before(first.element, new_nodes)
        for run in affected:
            paragraph.remove(run.element)

    def replace_text_minimal(self, paragraph: etree._Element, start: int, end: int, replacement: str) -> None:
        para_text, _ = paragraph_text_and_runs(paragraph)
        matched = para_text[start:end]
        prefix_len, original_suffix, replacement_start, replacement_end = narrow_replace_window(
            matched, replacement
        )
        narrowed_replacement = replacement[replacement_start:replacement_end]

        if prefix_len == len(matched) and prefix_len == len(replacement):
            return

        narrowed_start = start + prefix_len
        narrowed_end = start + original_suffix
        if narrowed_start == narrowed_end:
            self.insert_at(paragraph, narrowed_start, narrowed_replacement)
            return
        self.replace_span(paragraph, narrowed_start, narrowed_end, narrowed_replacement)

    def insert_at(self, paragraph: etree._Element, position: int, text: str) -> None:
        para_text, runs = paragraph_text_and_runs(paragraph)
        if not runs:
            raise PreciseRevisionError("段落中没有可编辑文本")

        if position == len(para_text):
            ins = make_revision("ins", self.take_id(), self.author, self.take_date(), text, runs[-1].element)
            if ins is not None:
                runs[-1].element.addnext(ins)
            return

        target_run = next((run for run in runs if run.start <= position <= run.end), None)
        if target_run is None:
            raise PreciseRevisionError("无法定位插入位置")

        if position == target_run.start:
            ins = make_revision("ins", self.take_id(), self.author, self.take_date(), text, target_run.element)
            if ins is not None:
                target_run.element.addprevious(ins)
            return

        if position == target_run.end:
            ins = make_revision("ins", self.take_id(), self.author, self.take_date(), text, target_run.element)
            if ins is not None:
                target_run.element.addnext(ins)
            return

        prefix = target_run.text[: position - target_run.start]
        suffix = target_run.text[position - target_run.start :]
        nodes: list[etree._Element] = []
        prefix_run = make_run_like(target_run.element, prefix)
        if prefix_run is not None:
            nodes.append(prefix_run)
        ins = make_revision("ins", self.take_id(), self.author, self.take_date(), text, target_run.element)
        if ins is not None:
            nodes.append(ins)
        suffix_run = make_run_like(target_run.element, suffix)
        if suffix_run is not None:
            nodes.append(suffix_run)
        self.insert_nodes_before(target_run.element, nodes)
        paragraph.remove(target_run.element)

    def apply(self, op: dict) -> None:
        op_type = op["type"]
        paragraph, start, end, _ = self.find_match(op)

        if op_type == "replace":
            self.replace_text_minimal(paragraph, start, end, op.get("replacement", ""))
            self.summary.append(f"replace: {op['target']} -> {op.get('replacement', '')}")
            return
        if op_type == "delete":
            self.replace_span(paragraph, start, end, None)
            self.summary.append(f"delete: {op['target']}")
            return
        if op_type == "insert_before":
            self.insert_at(paragraph, start, op["text"])
            self.summary.append(f"insert_before: {op['anchor']}")
            return
        if op_type == "insert_after":
            self.insert_at(paragraph, end, op["text"])
            self.summary.append(f"insert_after: {op['anchor']}")
            return
        raise PreciseRevisionError(f"不支持的操作类型: {op_type}")


def load_operations(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise PreciseRevisionError("操作文件必须是 JSON 数组")
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise PreciseRevisionError(f"第 {index} 个操作不是对象")
        if item.get("type") not in {"replace", "delete", "insert_before", "insert_after"}:
            raise PreciseRevisionError(f"第 {index} 个操作类型不支持: {item.get('type')!r}")
        op_type = item["type"]
        if op_type in {"replace", "delete"}:
            if not isinstance(item.get("target"), str) or not item["target"]:
                raise PreciseRevisionError(f"第 {index} 个操作缺少非空 target")
        if op_type == "replace" and not isinstance(item.get("replacement"), str):
            raise PreciseRevisionError(f"第 {index} 个 replace 操作缺少字符串 replacement")
        if op_type in {"insert_before", "insert_after"}:
            if not isinstance(item.get("anchor"), str) or not item["anchor"]:
                raise PreciseRevisionError(f"第 {index} 个插入操作缺少非空 anchor")
            if not isinstance(item.get("text"), str) or not item["text"]:
                raise PreciseRevisionError(f"第 {index} 个插入操作缺少非空 text")
        if "paragraph_hint" in item and not isinstance(item["paragraph_hint"], str):
            raise PreciseRevisionError(f"第 {index} 个操作的 paragraph_hint 必须是字符串")
        if "occurrence" in item and (
            not isinstance(item["occurrence"], int) or item["occurrence"] < 1
        ):
            raise PreciseRevisionError(f"第 {index} 个操作的 occurrence 必须是正整数")
        if item.get("allow_broad_change") is not None and not isinstance(
            item["allow_broad_change"], bool
        ):
            raise PreciseRevisionError(
                f"第 {index} 个操作的 allow_broad_change 必须是 true 或 false"
            )
    return data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="对合同 .docx 执行小粒度 Word 修订")
    parser.add_argument("docx_path")
    parser.add_argument("operations_json")
    parser.add_argument("--author", default="lawyer")
    parser.add_argument("--output")
    parser.add_argument("--in-place", action="store_true")
    parser.add_argument("--print-summary", action="store_true")
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="仅校验操作范围和目标锚点，不生成或修改 DOCX",
    )
    parser.add_argument("--start-time", help="修订起始时间，例如 2026-06-24T08:30:00+08:00")
    parser.add_argument("--interval-minutes", type=float, default=3)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    docx_path = Path(args.docx_path).expanduser().resolve()
    ops_path = Path(args.operations_json).expanduser().resolve()

    if not docx_path.exists():
        raise PreciseRevisionError(f"文件不存在: {docx_path}")
    if docx_path.suffix.lower() != ".docx":
        raise PreciseRevisionError("仅支持 .docx 文件")
    if not ops_path.exists():
        raise PreciseRevisionError(f"操作文件不存在: {ops_path}")

    if args.in_place and args.output:
        raise PreciseRevisionError("--in-place 与 --output 不能同时使用")

    start_time = parse_local_time(args.start_time)
    if args.in_place:
        output_path = docx_path
    elif args.output:
        output_path = Path(args.output).expanduser().resolve()
        if output_path == docx_path:
            raise PreciseRevisionError("如需覆盖原文件，请明确使用 --in-place")
    else:
        output_path = derive_output_path(docx_path, start_time)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    operations = load_operations(ops_path)
    broad_changes = validate_operations_scope(operations)

    temp_dir = Path(tempfile.mkdtemp(prefix="contract-precise-"))
    try:
        unzip_docx(docx_path, temp_dir)
        xml_paths = iter_xml_paths(temp_dir)
        trees = [etree.parse(str(path)) for path in xml_paths]
        applier = RevisionApplier(trees, args.author, start_time, args.interval_minutes)

        if args.check_only:
            for index, op in enumerate(operations, start=1):
                try:
                    applier.find_match(op)
                except PreciseRevisionError as exc:
                    raise PreciseRevisionError(f"第 {index} 个操作预检失败: {exc}") from exc
            print(f"预检通过：{len(operations)} 个操作的范围和锚点均有效。")
            if broad_changes:
                print(f"其中 {len(broad_changes)} 个结构性修订已声明理由：")
                for index, reason in broad_changes:
                    print(f"- 第 {index} 个操作：{reason}")
            return 0

        for index, op in enumerate(operations, start=1):
            try:
                applier.apply(op)
            except PreciseRevisionError as exc:
                raise PreciseRevisionError(f"第 {index} 个操作失败: {exc}") from exc

        for path, tree in zip(xml_paths, trees):
            tree.write(str(path), encoding="UTF-8", xml_declaration=True, pretty_print=False)

        temp_output = temp_dir.parent / f"{output_path.stem}.tmp{output_path.suffix}"
        if temp_output.exists():
            temp_output.unlink()
        zip_docx(temp_dir, temp_output)
        validate_docx_package(temp_output)
        temp_output.replace(output_path)

        if args.print_summary:
            print(f"输出文件: {output_path}")
            print(f"已完成 {len(applier.summary)} 处精准修订：")
            for line in applier.summary:
                print(f"- {line}")
            if broad_changes:
                print(f"结构性修订：{len(broad_changes)} 处")
                for index, reason in broad_changes:
                    print(f"- 第 {index} 个操作：{reason}")
        return 0
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PreciseRevisionError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1)
