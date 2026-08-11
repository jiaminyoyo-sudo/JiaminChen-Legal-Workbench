#!/usr/bin/env python3
"""Normalize Chinese font aliases in a DOCX for Word/LibreOffice portability."""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
FONT_MAP = {
    "仿宋_GB2312": "FangSong",
    "仿宋": "FangSong",
    "宋体": "SimSun",
    "黑体": "SimHei",
    "华文中宋": "STZhongsong",
    "楷体_GB2312": "KaiTi",
    "楷体": "KaiTi",
}


def _patch_xml(source: bytes) -> tuple[bytes, int]:
    root = ET.fromstring(source)
    changes = 0
    for element in root.iter():
        for attribute, value in list(element.attrib.items()):
            replacement = FONT_MAP.get(value)
            if replacement:
                element.set(attribute, replacement)
                changes += 1
        if element.tag == f"{{{W_NS}}}rFonts":
            hint = element.get(f"{{{W_NS}}}hint")
            east_asia = element.get(f"{{{W_NS}}}eastAsia")
            if hint == "eastAsia" and not east_asia:
                element.set(f"{{{W_NS}}}eastAsia", "SimSun")
                changes += 1
    if not changes:
        return source, 0
    return ET.tostring(root, encoding="utf-8", xml_declaration=True), changes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if not args.input.is_file():
        print(f"输入模板不存在：{args.input}", file=sys.stderr)
        return 2
    if args.output.exists() and not args.force:
        print(f"输出已存在；如需覆盖请加 --force：{args.output}", file=sys.stderr)
        return 2
    if args.input.resolve() == args.output.resolve():
        print("输入和输出必须使用不同路径", file=sys.stderr)
        return 2

    try:
        with zipfile.ZipFile(args.input, "r") as src:
            infos = src.infolist()
            contents = {info.filename: src.read(info.filename) for info in infos}
    except (OSError, zipfile.BadZipFile) as exc:
        print(f"无法读取 DOCX：{exc}", file=sys.stderr)
        return 2

    changed_parts: list[str] = []
    total_changes = 0
    for name, content in list(contents.items()):
        if not name.endswith(".xml"):
            continue
        try:
            patched, changes = _patch_xml(content)
        except ET.ParseError:
            continue
        if changes:
            contents[name] = patched
            changed_parts.append(name)
            total_changes += changes

    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(args.output, "w") as dst:
            for info in infos:
                dst.writestr(info, contents[info.filename])
    except OSError as exc:
        print(f"无法写入 DOCX：{exc}", file=sys.stderr)
        return 2

    print(f"normalized {total_changes} font references in {len(changed_parts)} parts")
    for name in changed_parts:
        print(name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
