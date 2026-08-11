#!/usr/bin/env python3
"""Audit generated lawyer-letter DOCX structure, margins, metadata and package preservation."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
DC_NS = "http://purl.org/dc/elements/1.1/"
CP_NS = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"


def qn(namespace: str, tag: str) -> str:
    return f"{{{namespace}}}{tag}"


REQUIRED_TEXT = [
    "编号：",
    "致：",
    "一、主要依据",
    "（一）事实依据",
    "（二）法律依据",
    "二、基本事实",
    "三、法律责任",
    "四、本律师意见",
    "特此函告",
    "律师事务所",
    "（本函加盖本所公章及骑缝章后发出）",
    "附件：",
]


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def audit(docx: Path, template: Path | None = None) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    with zipfile.ZipFile(docx, "r") as archive:
        names = archive.namelist()
        contents = {name: archive.read(name) for name in names}
    if "word/document.xml" not in contents:
        return {"valid": False, "errors": ["缺少 word/document.xml"], "warnings": []}

    root = ET.fromstring(contents["word/document.xml"])
    text = "\n".join(node.text or "" for node in root.iter(qn(W_NS, "t")))
    normalized_title = text.replace(" ", "")
    if "律师函" not in normalized_title:
        errors.append("缺少律师函标题")
    for marker in REQUIRED_TEXT:
        if marker not in text:
            errors.append(f"缺少11部分结构标记：{marker}")
    if text.count("经办律师：") < 2:
        errors.append("经办律师手签栏少于两处")

    sect_pr = root.find(f".//{qn(W_NS, 'sectPr')}")
    if sect_pr is None:
        errors.append("缺少节属性")
    else:
        pg_mar = sect_pr.find(qn(W_NS, "pgMar"))
        expected = {"top": "1440", "bottom": "1440", "left": "1803", "right": "1803"}
        if pg_mar is None:
            errors.append("缺少页边距设置")
        else:
            for key, value in expected.items():
                if pg_mar.get(qn(W_NS, key)) != value:
                    errors.append(f"页边距 {key} 不符合标准：应为 {value}")

    if "docProps/core.xml" in contents:
        core = ET.fromstring(contents["docProps/core.xml"])
        creator = core.find(qn(DC_NS, "creator"))
        modifier = core.find(qn(CP_NS, "lastModifiedBy"))
        if creator is None or creator.text != "大成律师":
            errors.append("Word 作者不是大成律师")
        if modifier is None or modifier.text != "大成律师":
            errors.append("Word 最后修改者不是大成律师")

    changed_parts: list[str] = []
    if template:
        with zipfile.ZipFile(template, "r") as archive:
            template_names = archive.namelist()
            template_contents = {name: archive.read(name) for name in template_names}
        if names != template_names:
            errors.append("生成稿的 DOCX 包部件清单与信头模板不一致")
        for name in sorted(set(names) & set(template_names)):
            if _sha256(contents[name]) != _sha256(template_contents[name]):
                changed_parts.append(name)
        allowed = {"word/document.xml", "docProps/core.xml"}
        unexpected = [name for name in changed_parts if name not in allowed]
        if unexpected:
            errors.append("非预期包部件发生变化：" + "、".join(unexpected))

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "changed_parts": changed_parts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("docx", type=Path)
    parser.add_argument("--template", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if not args.docx.is_file():
        print(f"DOCX 不存在：{args.docx}", file=sys.stderr)
        return 2
    if args.template and not args.template.is_file():
        print(f"模板不存在：{args.template}", file=sys.stderr)
        return 2
    try:
        report = audit(args.docx, args.template)
    except (OSError, zipfile.BadZipFile, ET.ParseError) as exc:
        print(f"审计失败：{exc}", file=sys.stderr)
        return 2
    output = json.dumps(report, ensure_ascii=False, indent=2)
    print(output)
    if args.report:
        args.report.write_text(output + "\n", encoding="utf-8")
    return 0 if report["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
