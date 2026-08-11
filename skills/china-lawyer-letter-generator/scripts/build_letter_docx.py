#!/usr/bin/env python3
"""Build a fixed-structure Chinese lawyer-letter DOCX on retained Dentons letterhead."""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

from validate_matter import validate


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_NS = "http://www.w3.org/XML/1998/namespace"
CP_NS = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
DC_NS = "http://purl.org/dc/elements/1.1/"
DCTERMS_NS = "http://purl.org/dc/terms/"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"

ET.register_namespace("w", W_NS)
ET.register_namespace("cp", CP_NS)
ET.register_namespace("dc", DC_NS)
ET.register_namespace("dcterms", DCTERMS_NS)
ET.register_namespace("xsi", XSI_NS)


def qn(namespace: str, tag: str) -> str:
    return f"{{{namespace}}}{tag}"


def _set_val(parent: ET.Element, tag: str, value: str) -> ET.Element:
    child = ET.SubElement(parent, qn(W_NS, tag))
    child.set(qn(W_NS, "val"), value)
    return child


def _paragraph(
    text: str = "",
    *,
    role: str = "body",
    alignment: str = "both",
    first_line: bool = False,
    keep_next: bool = False,
    page_break_before: bool = False,
    bold_override: bool | None = None,
) -> ET.Element:
    """Create one fully formatted paragraph without relying on Word defaults."""
    p = ET.Element(qn(W_NS, "p"))
    p_pr = ET.SubElement(p, qn(W_NS, "pPr"))

    role_tokens = {
        "title": ("STZhongsong", "36", True, "240"),
        "reference": ("SimSun", "24", False, "0"),
        "summary": ("SimHei", "24", True, "0"),
        "heading": ("SimHei", "24", True, "0"),
        "subheading": ("SimHei", "24", True, "0"),
        "body": ("SimSun", "24", False, "0"),
        "signature": ("SimSun", "24", False, "0"),
        "note": ("SimSun", "21", False, "0"),
    }
    font, size, default_bold, after = role_tokens.get(role, role_tokens["body"])
    bold = default_bold if bold_override is None else bold_override

    spacing = ET.SubElement(p_pr, qn(W_NS, "spacing"))
    spacing.set(qn(W_NS, "before"), "0")
    spacing.set(qn(W_NS, "after"), after)
    spacing.set(qn(W_NS, "line"), "360")
    spacing.set(qn(W_NS, "lineRule"), "auto")
    _set_val(p_pr, "jc", alignment)
    if first_line:
        indent = ET.SubElement(p_pr, qn(W_NS, "ind"))
        indent.set(qn(W_NS, "firstLine"), "480")
    if keep_next:
        ET.SubElement(p_pr, qn(W_NS, "keepNext"))
    if page_break_before:
        ET.SubElement(p_pr, qn(W_NS, "pageBreakBefore"))

    run = ET.SubElement(p, qn(W_NS, "r"))
    r_pr = ET.SubElement(run, qn(W_NS, "rPr"))
    fonts = ET.SubElement(r_pr, qn(W_NS, "rFonts"))
    fonts.set(qn(W_NS, "ascii"), "Times New Roman")
    fonts.set(qn(W_NS, "hAnsi"), "Times New Roman")
    fonts.set(qn(W_NS, "eastAsia"), font)
    fonts.set(qn(W_NS, "cs"), font)
    fonts.set(qn(W_NS, "hint"), "eastAsia")
    _set_val(r_pr, "sz", size)
    _set_val(r_pr, "szCs", size)
    lang = ET.SubElement(r_pr, qn(W_NS, "lang"))
    lang.set(qn(W_NS, "eastAsia"), "zh-CN")
    if bold:
        ET.SubElement(r_pr, qn(W_NS, "b"))
        ET.SubElement(r_pr, qn(W_NS, "bCs"))

    t = ET.SubElement(run, qn(W_NS, "t"))
    t.set(qn(XML_NS, "space"), "preserve")
    t.text = text
    return p


def _as_items(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, (str, int, float)):
        text = str(value).strip()
        return [{"text": text}] if text else []
    if not isinstance(value, list):
        return [{"text": str(value)}]
    items: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, dict):
            text = str(item.get("text") or "").strip()
            if text:
                spec = dict(item)
                spec["text"] = text
                items.append(spec)
        else:
            text = str(item).strip()
            if text:
                items.append({"text": text})
    return items


def _append_items(
    paragraphs: list[ET.Element],
    value: Any,
    *,
    placeholder: str,
    numbered: bool = False,
    first_line: bool = True,
    role: str = "body",
) -> None:
    items = _as_items(value) or [{"text": placeholder}]
    for index, item in enumerate(items, start=1):
        text = str(item["text"])
        if numbered and not re.match(r"^\s*(?:\d+[.．、]|[（(][一二三四五六七八九十0-9]+[）)])", text):
            text = f"{index}. {text}"
        paragraphs.append(
            _paragraph(
                text,
                role=str(item.get("role") or role),
                alignment=str(item.get("alignment") or "both"),
                first_line=bool(item.get("first_line", first_line)),
                bold_override=item.get("bold") if isinstance(item.get("bold"), bool) else None,
            )
        )


def _unique_evidence(data: dict[str, Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for fact in data.get("facts", []):
        if not isinstance(fact, dict) or not fact.get("include_in_letter", True):
            continue
        for item in fact.get("evidence", []):
            text = str(item).strip()
            if text and text not in seen:
                seen.add(text)
                result.append(text)
    return result


def _verified_legal_basis(data: dict[str, Any]) -> list[str]:
    grouped: dict[str, list[str]] = {}
    for source in data.get("legal_sources", []):
        if not isinstance(source, dict) or source.get("verified") is not True:
            continue
        name = str(source.get("name") or "").strip()
        article = str(source.get("article") or "").strip()
        if name:
            clean_name = name.strip("《》")
            grouped.setdefault(clean_name, [])
            if article and article not in grouped[clean_name]:
                grouped[clean_name].append(article)
    return [
        f"《{name}》{'、'.join(articles)}" if articles else f"《{name}》"
        for name, articles in grouped.items()
    ]


def _legacy_blocks(document: dict[str, Any]) -> tuple[Any, Any, Any]:
    sections = document.get("sections")
    if not isinstance(sections, list):
        return [], [], []
    blocks = [
        section.get("paragraphs", [])
        for section in sections
        if isinstance(section, dict)
    ]
    basic_facts = blocks[0] if blocks else []
    legal_liability = blocks[1] if len(blocks) > 1 else []
    lawyer_opinion: list[Any] = []
    for block in blocks[2:]:
        if isinstance(block, list):
            lawyer_opinion.extend(block)
        elif block:
            lawyer_opinion.append(block)
    return basic_facts, legal_liability, lawyer_opinion


_CN_DIGITS = "〇一二三四五六七八九"


def _cn_number(value: int) -> str:
    if value < 10:
        return _CN_DIGITS[value]
    tens, ones = divmod(value, 10)
    prefix = "" if tens == 1 else _CN_DIGITS[tens]
    return f"{prefix}十{_CN_DIGITS[ones] if ones else ''}"


def _cn_date(value: date) -> str:
    year = "".join(_CN_DIGITS[int(digit)] for digit in str(value.year))
    return f"{year}年{_cn_number(value.month)}月{_cn_number(value.day)}日"


def _format_issue_date(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return _cn_date(datetime.now(ZoneInfo("Asia/Shanghai")).date())
    try:
        return _cn_date(date.fromisoformat(text))
    except ValueError:
        return text


def _default_reference_no(document: dict[str, Any]) -> str:
    year = datetime.now(ZoneInfo("Asia/Shanghai")).year
    prefix = str(document.get("reference_prefix") or "川大成函字").strip()
    return f"（{year}）{prefix}第〔待编号〕号"


def _signature_line(name: str) -> str:
    clean = name.strip()
    if not clean:
        return "经办律师：＿＿＿＿＿＿＿＿（手签）"
    if clean.startswith("经办律师"):
        return clean
    return f"经办律师：{clean}（手签）"


def _build_paragraphs(data: dict[str, Any]) -> list[ET.Element]:
    document = data.get("document", {})
    status = data.get("status", "draft")
    paragraphs: list[ET.Element] = []

    title = str(document.get("title") or "律 师 函").strip()
    paragraphs.append(_paragraph(title, role="title", alignment="center"))

    reference_no = str(document.get("reference_no") or "").strip() or _default_reference_no(document)
    label = reference_no if reference_no.startswith("编号") else f"编号：{reference_no}"
    paragraphs.append(_paragraph(label, role="reference", alignment="right"))

    subject = str(document.get("subject") or "〔待补充主张事项摘要〕").strip()
    paragraphs.append(_paragraph(subject, role="summary", alignment="left"))

    recipient_line = str(document.get("recipient_line") or "").strip()
    if not recipient_line and str(data.get("recipient") or "").strip():
        recipient_line = f"致：{str(data['recipient']).strip()}"
    paragraphs.append(
        _paragraph(recipient_line or "致：〔待核实收件人〕", role="summary", alignment="left")
    )

    _append_items(
        paragraphs,
        document.get("opening"),
        placeholder="〔待根据委托关系、签发事项和已核事实补充首部〕",
    )

    paragraphs.append(_paragraph("一、主要依据", role="heading", alignment="left", keep_next=True))
    paragraphs.append(_paragraph("（一）事实依据", role="subheading", alignment="left", keep_next=True))
    main_basis = document.get("main_basis")
    if not isinstance(main_basis, dict):
        main_basis = {}
    fact_basis = main_basis.get("fact_basis") or _unique_evidence(data)
    _append_items(
        paragraphs,
        fact_basis,
        placeholder="〔待列明实际已取得并拟作为本函依据的基础材料〕",
        numbered=True,
    )
    paragraphs.append(_paragraph("（二）法律依据", role="subheading", alignment="left", keep_next=True))
    legal_basis = main_basis.get("legal_basis") or _verified_legal_basis(data)
    _append_items(
        paragraphs,
        legal_basis,
        placeholder="〔待核验并列明与本案主张直接相关的法律依据；正文不列条号时据实调整〕",
        numbered=True,
    )

    legacy_facts, legacy_liability, legacy_opinion = _legacy_blocks(document)
    paragraphs.append(_paragraph("二、基本事实", role="heading", alignment="left", keep_next=True))
    _append_items(
        paragraphs,
        document.get("basic_facts") or legacy_facts,
        placeholder="〔待根据已核事实、委托人陈述及证据范围起草基本事实〕",
    )

    paragraphs.append(_paragraph("三、法律责任", role="heading", alignment="left", keep_next=True))
    _append_items(
        paragraphs,
        document.get("legal_liability") or legacy_liability,
        placeholder="〔待结合合同约定、现行法律和函件目的分析责任或法律后果〕",
    )

    paragraphs.append(_paragraph("四、本律师意见", role="heading", alignment="left", keep_next=True))
    _append_items(
        paragraphs,
        document.get("lawyer_opinion") or legacy_opinion,
        placeholder="〔待写明具体要求、履行期限、反馈方式及不履行后果〕",
    )

    closing = document.get("closing") or [
        "为避免争议进一步扩大并造成不必要损失，望贵方审慎对待本函所述事实、法律责任及本律师意见，及时作出实质、有效回应。"
    ]
    _append_items(paragraphs, closing, placeholder="〔待结合签发目的调整结尾〕")
    copy_statement = str(
        document.get("copy_statement")
        or "本函一式两份，一份送达贵方，一份留存本所备查。"
    ).strip()
    if copy_statement:
        paragraphs.append(_paragraph(copy_statement, first_line=True))
    closing_phrase = str(document.get("closing_phrase") or "特此函告。").strip()
    paragraphs.append(_paragraph(closing_phrase, first_line=True))

    firm = str(document.get("firm") or "北京大成（成都）律师事务所").strip()
    lawyers = [str(item).strip() for item in document.get("lawyers", []) if str(item).strip()]
    while len(lawyers) < 2:
        lawyers.append("")
    signature_lines = [
        firm,
        _signature_line(lawyers[0]),
        _signature_line(lawyers[1]),
        _format_issue_date(document.get("issue_date")),
        str(document.get("stamp_note") or "（本函加盖本所公章及骑缝章后发出）").strip(),
    ]
    paragraphs.append(_paragraph("", role="signature", alignment="right", keep_next=True))
    for index, line in enumerate(signature_lines):
        paragraphs.append(
            _paragraph(
                line,
                role="note" if index == len(signature_lines) - 1 else "signature",
                alignment="right",
                keep_next=index < len(signature_lines) - 1,
            )
        )

    attachments = [str(item).strip() for item in document.get("attachments", []) if str(item).strip()]
    no_attachments = document.get("no_attachments") is True
    if attachments:
        paragraphs.append(
            _paragraph("附件：", role="heading", alignment="left", keep_next=True, page_break_before=True)
        )
        for index, attachment in enumerate(attachments, start=1):
            paragraphs.append(_paragraph(f"{index}. {attachment}", alignment="left", first_line=True))
    elif no_attachments:
        paragraphs.append(_paragraph("附件：无", role="heading", alignment="left"))
    else:
        paragraphs.append(
            _paragraph(
                "附件：〔请根据实际附送材料填写；无附件请改为“无”〕",
                role="heading",
                alignment="left",
                page_break_before=status == "draft",
            )
        )

    return paragraphs


def _set_section_margins(sect_pr: ET.Element) -> None:
    """Apply the internal lawyer-letter margins while retaining section furniture."""
    pg_mar = sect_pr.find(qn(W_NS, "pgMar"))
    if pg_mar is None:
        pg_mar = ET.SubElement(sect_pr, qn(W_NS, "pgMar"))
    pg_mar.set(qn(W_NS, "top"), "1440")
    pg_mar.set(qn(W_NS, "bottom"), "1440")
    pg_mar.set(qn(W_NS, "left"), "1803")
    pg_mar.set(qn(W_NS, "right"), "1803")


def _patch_document_xml(source: bytes, data: dict[str, Any]) -> bytes:
    root = ET.fromstring(source)
    body = root.find(qn(W_NS, "body"))
    if body is None:
        raise ValueError("模板缺少 word/document.xml 的 w:body")
    sect_pr = body.find(qn(W_NS, "sectPr"))
    if sect_pr is None:
        raise ValueError("模板缺少节属性，无法安全保留信头")
    sect_copy = copy.deepcopy(sect_pr)
    _set_section_margins(sect_copy)
    for child in list(body):
        body.remove(child)
    for paragraph in _build_paragraphs(data):
        body.append(paragraph)
    body.append(sect_copy)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _patch_core_xml(source: bytes) -> bytes:
    root = ET.fromstring(source)
    creator = root.find(qn(DC_NS, "creator"))
    if creator is None:
        creator = ET.SubElement(root, qn(DC_NS, "creator"))
    creator.text = "大成律师"
    modifier = root.find(qn(CP_NS, "lastModifiedBy"))
    if modifier is None:
        modifier = ET.SubElement(root, qn(CP_NS, "lastModifiedBy"))
    modifier.text = "大成律师"
    modified = root.find(qn(DCTERMS_NS, "modified"))
    if modified is None:
        modified = ET.SubElement(root, qn(DCTERMS_NS, "modified"))
    modified.set(qn(XSI_NS, "type"), "dcterms:W3CDTF")
    modified.text = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _write_docx(template: Path, output: Path, data: dict[str, Any]) -> None:
    with zipfile.ZipFile(template, "r") as src:
        infos = src.infolist()
        contents = {info.filename: src.read(info.filename) for info in infos}
    if "word/document.xml" not in contents:
        raise ValueError("输入文件不是有效的 Word 模板")
    contents["word/document.xml"] = _patch_document_xml(contents["word/document.xml"], data)
    if "docProps/core.xml" in contents:
        contents["docProps/core.xml"] = _patch_core_xml(contents["docProps/core.xml"])

    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w") as dst:
        for info in infos:
            dst.writestr(info, contents[info.filename])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Matter JSON")
    parser.add_argument("--template", type=Path, help="Retained letterhead DOCX")
    parser.add_argument("--output", required=True, type=Path, help="Output DOCX")
    parser.add_argument("--force", action="store_true", help="Overwrite output if it exists")
    args = parser.parse_args()

    skill_dir = Path(__file__).resolve().parent.parent
    template = args.template or skill_dir / "assets" / "大成成都信头纸模板.docx"
    if not args.input.is_file():
        print(f"事项 JSON 不存在：{args.input}", file=sys.stderr)
        return 2
    if not template.is_file():
        print(f"信头模板不存在：{template}", file=sys.stderr)
        return 2
    if args.output.exists() and not args.force:
        print(f"输出已存在；如需覆盖请加 --force：{args.output}", file=sys.stderr)
        return 2

    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"无法读取事项 JSON：{exc}", file=sys.stderr)
        return 2
    if not isinstance(data, dict):
        print("事项 JSON 顶层必须是对象", file=sys.stderr)
        return 2

    errors, warnings = validate(data)
    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 2

    try:
        _write_docx(template, args.output, data)
    except (OSError, ValueError, zipfile.BadZipFile, ET.ParseError) as exc:
        print(f"生成失败：{exc}", file=sys.stderr)
        return 2
    print(str(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
