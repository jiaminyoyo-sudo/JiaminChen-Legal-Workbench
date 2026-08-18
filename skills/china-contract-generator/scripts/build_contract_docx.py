#!/usr/bin/env python3
"""Build a clean Chinese contract DOCX from a UTF-8 plain-text draft.

The script uses only the Python standard library. Each non-empty source line is
treated as one paragraph. The first non-empty line is the document title unless
``--title`` is supplied.

Supported source markers:
  [[PAGE_BREAK]]       insert a page break
  [[SIGNATURE_PAGE]]   start a new signature page
  [[CENTER]]text       render one centered paragraph
  [[NO_INDENT]]text    render one paragraph without first-line indentation
"""

from __future__ import annotations

import argparse
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree
from xml.sax.saxutils import escape


CLAUSE_RE = re.compile(r"^第[〇零一二三四五六七八九十百千万0-9]+[编章节条](?:\s|　|$)")
TOP_HEADING_RE = re.compile(r"^[一二三四五六七八九十百]+[、.]\s*")
NO_INDENT_RE = re.compile(
    r"^(甲方|乙方|丙方|丁方|法定代表人|负责人|授权代表|联系人|地址|电话|"
    r"电子邮箱|开户行|账号|统一社会信用代码|签署日期|附件)[：:]"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a clean Chinese contract DOCX from UTF-8 plain text."
    )
    parser.add_argument("input", type=Path, help="UTF-8 plain-text contract draft")
    parser.add_argument("output", type=Path, help="Output .docx path")
    parser.add_argument("--title", help="Document title; otherwise use first non-empty line")
    parser.add_argument("--author", default="lawyer", help="DOCX core-property author")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing output")
    return parser.parse_args()


def run_xml(text: str) -> str:
    parts = text.split("\t")
    runs: list[str] = []
    for index, part in enumerate(parts):
        if index:
            runs.append("<w:r><w:tab/></w:r>")
        if part:
            preserve = ' xml:space="preserve"' if part[:1].isspace() or part[-1:].isspace() else ""
            runs.append(f"<w:r><w:t{preserve}>{escape(part)}</w:t></w:r>")
    return "".join(runs) or "<w:r><w:t/></w:r>"


def paragraph_xml(text: str, style: str = "Normal", page_break_before: bool = False) -> str:
    page_break = '<w:pageBreakBefore w:val="1"/>' if page_break_before else ""
    return (
        "<w:p><w:pPr>"
        f'<w:pStyle w:val="{style}"/>{page_break}'
        "</w:pPr>"
        f"{run_xml(text)}"
        "</w:p>"
    )


def page_break_xml() -> str:
    return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'


def select_style(line: str, signature_mode: bool) -> str:
    if signature_mode:
        return "Signature"
    if CLAUSE_RE.match(line):
        return "ClauseHeading"
    if TOP_HEADING_RE.match(line):
        return "SubHeading"
    if NO_INDENT_RE.match(line) or line in {"鉴于：", "兹约定如下："}:
        return "NoIndent"
    return "Normal"


def build_document_xml(title: str, body_lines: list[str]) -> str:
    body: list[str] = [paragraph_xml(title, "ContractTitle")]
    signature_mode = False

    for raw_line in body_lines:
        line = raw_line.strip()
        if not line:
            continue
        if line == "[[PAGE_BREAK]]":
            body.append(page_break_xml())
            continue
        if line == "[[SIGNATURE_PAGE]]":
            body.append(
                paragraph_xml(
                    "（以下无正文，为本合同签署页）",
                    "Center",
                    page_break_before=True,
                )
            )
            signature_mode = True
            continue
        if line.startswith("[[CENTER]]"):
            body.append(paragraph_xml(line.removeprefix("[[CENTER]]").strip(), "Center"))
            continue
        if line.startswith("[[NO_INDENT]]"):
            body.append(paragraph_xml(line.removeprefix("[[NO_INDENT]]").strip(), "NoIndent"))
            continue
        body.append(paragraph_xml(line, select_style(line, signature_mode)))

    section = """
<w:sectPr>
  <w:footerReference w:type="default" r:id="rId4"/>
  <w:pgSz w:w="11906" w:h="16838"/>
  <w:pgMar w:top="1440" w:right="1701" w:bottom="1440" w:left="1701" w:header="720" w:footer="720" w:gutter="0"/>
  <w:cols w:space="720"/>
  <w:docGrid w:type="lines" w:linePitch="312"/>
</w:sectPr>
"""
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<w:body>{''.join(body)}{section}</w:body>
</w:document>
"""


def styles_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:docDefaults>
    <w:rPrDefault><w:rPr>
      <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="宋体"/>
      <w:sz w:val="24"/><w:szCs w:val="24"/><w:lang w:val="zh-CN" w:eastAsia="zh-CN"/>
    </w:rPr></w:rPrDefault>
    <w:pPrDefault><w:pPr>
      <w:spacing w:before="0" w:after="0" w:line="360" w:lineRule="auto"/>
      <w:jc w:val="both"/><w:ind w:firstLineChars="200"/>
    </w:pPr></w:pPrDefault>
  </w:docDefaults>
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/><w:qFormat/>
    <w:pPr><w:spacing w:before="0" w:after="0" w:line="360" w:lineRule="auto"/><w:jc w:val="both"/><w:ind w:firstLineChars="200"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="宋体"/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="ContractTitle">
    <w:name w:val="Contract Title"/><w:basedOn w:val="Normal"/><w:qFormat/>
    <w:pPr><w:keepNext/><w:spacing w:before="240" w:after="480"/><w:jc w:val="center"/><w:ind w:firstLineChars="0"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:eastAsia="黑体"/><w:b/><w:sz w:val="36"/><w:szCs w:val="36"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="ClauseHeading">
    <w:name w:val="Clause Heading"/><w:basedOn w:val="Normal"/><w:qFormat/>
    <w:pPr><w:keepNext/><w:spacing w:before="160" w:after="40"/><w:ind w:firstLineChars="0"/></w:pPr>
    <w:rPr><w:b/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="SubHeading">
    <w:name w:val="Sub Heading"/><w:basedOn w:val="Normal"/><w:qFormat/>
    <w:pPr><w:keepNext/><w:spacing w:before="80" w:after="20"/><w:ind w:firstLineChars="0"/></w:pPr>
    <w:rPr><w:b/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="NoIndent">
    <w:name w:val="No Indent"/><w:basedOn w:val="Normal"/>
    <w:pPr><w:ind w:firstLineChars="0"/><w:jc w:val="left"/></w:pPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Center">
    <w:name w:val="Center"/><w:basedOn w:val="Normal"/>
    <w:pPr><w:spacing w:before="120" w:after="120"/><w:ind w:firstLineChars="0"/><w:jc w:val="center"/></w:pPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Signature">
    <w:name w:val="Signature"/><w:basedOn w:val="Normal"/>
    <w:pPr><w:spacing w:before="0" w:after="180"/><w:ind w:firstLineChars="0"/><w:jc w:val="left"/></w:pPr>
  </w:style>
</w:styles>
"""


def package_parts(title: str, author: str, body_lines: list[str]) -> dict[str, str]:
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    title_attr = escape(title)
    author_attr = escape(author)
    return {
        "[Content_Types].xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>
  <Override PartName="/word/fontTable.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.fontTable+xml"/>
  <Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>
""",
        "_rels/.rels": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
""",
        "docProps/core.xml": f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
 xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/"
 xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>{title_attr}</dc:title><dc:creator>{author_attr}</dc:creator>
  <cp:lastModifiedBy>{author_attr}</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>
</cp:coreProperties>
""",
        "docProps/app.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
 xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Contract DOCX Fallback</Application><DocSecurity>0</DocSecurity><ScaleCrop>false</ScaleCrop>
  <Company></Company><LinksUpToDate>false</LinksUpToDate><SharedDoc>false</SharedDoc><HyperlinksChanged>false</HyperlinksChanged><AppVersion>1.0</AppVersion>
</Properties>
""",
        "word/document.xml": build_document_xml(title, body_lines),
        "word/styles.xml": styles_xml(),
        "word/settings.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:zoom w:percent="100"/><w:defaultTabStop w:val="420"/><w:characterSpacingControl w:val="doNotCompress"/>
  <w:compat><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat>
</w:settings>
""",
        "word/fontTable.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:fonts xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:font w:name="宋体"><w:family w:val="roman"/><w:charset w:val="86"/></w:font>
  <w:font w:name="黑体"><w:family w:val="swiss"/><w:charset w:val="86"/></w:font>
  <w:font w:name="Times New Roman"><w:family w:val="roman"/><w:charset w:val="00"/></w:font>
</w:fonts>
""",
        "word/footer1.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:p><w:pPr><w:jc w:val="center"/></w:pPr>
    <w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r>
  </w:p>
</w:ftr>
""",
        "word/_rels/document.xml.rels": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/fontTable" Target="fontTable.xml"/>
  <Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>
</Relationships>
""",
    }


def write_docx(output: Path, parts: dict[str, str], overwrite: bool) -> None:
    if output.suffix.lower() != ".docx":
        raise ValueError("Output path must end with .docx")
    if output.exists() and not overwrite:
        raise FileExistsError(f"Output already exists: {output}; use --overwrite to replace it")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in parts.items():
            archive.writestr(name, content.encode("utf-8"))


def validate_docx(path: Path) -> None:
    required = {
        "[Content_Types].xml",
        "_rels/.rels",
        "word/document.xml",
        "word/styles.xml",
        "word/settings.xml",
        "word/fontTable.xml",
        "word/footer1.xml",
        "word/_rels/document.xml.rels",
        "docProps/core.xml",
        "docProps/app.xml",
    }
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        missing = required - names
        if missing:
            raise ValueError(f"DOCX package is missing: {', '.join(sorted(missing))}")
        for name in required:
            ElementTree.fromstring(archive.read(name))


def main() -> int:
    args = parse_args()
    if not args.input.is_file():
        print(f"Input file not found: {args.input}", file=sys.stderr)
        return 2
    source = args.input.read_text(encoding="utf-8-sig")
    lines = source.splitlines()
    non_empty_indexes = [index for index, line in enumerate(lines) if line.strip()]
    if not non_empty_indexes:
        print("Input contains no contract text", file=sys.stderr)
        return 2

    if args.title:
        title = args.title.strip()
        body_lines = lines
    else:
        title_index = non_empty_indexes[0]
        title = lines[title_index].strip()
        body_lines = lines[title_index + 1 :]

    if not title:
        print("Document title cannot be empty", file=sys.stderr)
        return 2

    try:
        write_docx(
            args.output,
            package_parts(title, args.author, body_lines),
            overwrite=args.overwrite,
        )
        validate_docx(args.output)
    except Exception as exc:
        print(f"DOCX generation failed: {exc}", file=sys.stderr)
        return 1

    print(f"Created: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
