#!/usr/bin/env python3
"""Audit a BSE private-placement investor-side legal opinion DOCX or TXT."""

from __future__ import annotations

import argparse
from datetime import date
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}

REQUIRED_SECTIONS = [
    "本次投资的交易方案",
    "主体资格",
    "本次投资前的授权与批准",
    "股份登记",
    "股份锁定期",
    "本次认购文件及后续签约安排",
    "结论意见",
]

HIGH_RISK_PATTERNS = {
    "旧适当性规则名称": r"北京证券交易所投资者适当性管理办法（试行）",
    "错误板块名称": r"北京证券交易所科创板",
    "不规范登记简称": r"中证登公司",
    "未按投资人要求的审核注册完成后拟制时点撰写": r"本次发行(?:尚处于|仍处于|目前处于).{0,20}(?:北交所)?审核阶段|本次发行尚需.{0,30}北交所审核",
    "不存在合同却承诺后续审查": r"提交本所审查",
    "不存在合同却作空泛保留": r"尚未取得拟签署的《认购合同》文本.{0,30}暂不对",
}

PLACEHOLDER_PATTERNS = [
    r"【[^】]*】",
    r"\[TODO[^\]]*\]",
    r"待补充|待确认|待核实|待编号",
]

APPROVAL_SENSITIVE_PLACEHOLDERS = [
    "北交所于【】出具的【】",
    "证监许可〔【年份】〕【文号】号",
    "【募集资金上限】",
    "【发行数量上限】",
]

RULE_TITLE_HINTS = ("法", "条例", "办法", "规定", "规则", "指引", "指南", "通知", "决定")
OFFICIAL_BASE_DOMAINS = ("gov.cn", "bse.cn", "chinaclear.cn")
CITATION_RE = re.compile(
    r"《(?P<title>[^》]+)》(?P<article>第[零〇一二三四五六七八九十百千0-9]+条"
    r"(?:第[零〇一二三四五六七八九十百千0-9]+款)?"
    r"(?:第[零〇一二三四五六七八九十百千0-9]+项)?)"
)
VERBATIM_RE = re.compile(
    r"《(?P<title>[^》]+)》(?P<article>第[零〇一二三四五六七八九十百千0-9]+条"
    r"(?:第[零〇一二三四五六七八九十百千0-9]+款)?"
    r"(?:第[零〇一二三四五六七八九十百千0-9]+项)?)规定[，,:：]?\s*[“\"](?P<quote>.*?)[”\"]",
    re.S,
)

CONCLUSION_TOPICS = {
    "主体资格": ("主体资格",),
    "国资审核或系统备案": ("审核批准", "管理信息系统", "统一编号"),
    "股份登记": ("股份登记", "中国结算"),
    "股份限售": ("限售", "不得转让"),
    "国有属性标识": ("SS", "CS", "国有股东标识", "国有属性"),
    "认购程序": ("认购邀请书", "申购报价", "认购合同", "缴款"),
}


def qname(local: str) -> str:
    return f"{{{W_NS}}}{local}"


def read_docx(path: Path) -> tuple[str, dict[str, Any]]:
    paragraphs: list[str] = []
    flags: dict[str, Any] = {
        "tracked_changes": False,
        "comments": False,
        "comment_anchors": [],
    }
    with zipfile.ZipFile(path) as zf:
        names = set(zf.namelist())
        flags["comments"] = "word/comments.xml" in names
        comments: dict[str, str] = {}
        if flags["comments"]:
            comments_root = ET.fromstring(zf.read("word/comments.xml"))
            for comment in comments_root.findall(".//w:comment", NS):
                comment_id = comment.attrib.get(qname("id"), "")
                comments[comment_id] = "".join(
                    node.text or "" for node in comment.iter(qname("t"))
                ).strip()
        root = ET.fromstring(zf.read("word/document.xml"))
        flags["tracked_changes"] = bool(root.findall(".//w:ins", NS) or root.findall(".//w:del", NS))
        active_comments: list[str] = []
        anchors: dict[str, list[str]] = {comment_id: [] for comment_id in comments}
        for p in root.findall(".//w:p", NS):
            parts: list[str] = []
            for node in p.iter():
                if node.tag == qname("commentRangeStart"):
                    comment_id = node.attrib.get(qname("id"), "")
                    if comment_id not in active_comments:
                        active_comments.append(comment_id)
                    continue
                if node.tag == qname("commentRangeEnd"):
                    comment_id = node.attrib.get(qname("id"), "")
                    if comment_id in active_comments:
                        active_comments.remove(comment_id)
                    continue
                if node.tag == qname("delText"):
                    continue
                if node.tag == qname("t") and node.text:
                    piece = node.text
                elif node.tag == qname("tab"):
                    piece = "\t"
                elif node.tag == qname("br"):
                    piece = "\n"
                else:
                    continue
                parts.append(piece)
                for comment_id in active_comments:
                    anchors.setdefault(comment_id, []).append(piece)
            text = "".join(parts).strip()
            if text:
                paragraphs.append(text)
        flags["comment_anchors"] = [
            {
                "id": comment_id,
                "anchor": "".join(anchors.get(comment_id, [])).strip(),
                "comment": comment_text,
            }
            for comment_id, comment_text in comments.items()
        ]
    return "\n".join(paragraphs), flags


def read_input(path: Path) -> tuple[str, dict[str, Any]]:
    if path.suffix.lower() == ".docx":
        return read_docx(path)
    return path.read_text(encoding="utf-8"), {"tracked_changes": False, "comments": False}


def normalize_verbatim(text: str) -> str:
    """Ignore layout whitespace only; punctuation and wording must remain unchanged."""
    return re.sub(r"\s+", "", text)


def load_source_ledger(path: Path | None) -> tuple[dict[str, Any] | None, list[str]]:
    if path is None:
        return None, []
    if not path.exists():
        return None, [f"法律依据核验台账不存在：{path}"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, [f"法律依据核验台账无法读取：{exc}"]
    if not isinstance(data, dict) or not isinstance(data.get("rules"), list):
        return None, ["法律依据核验台账格式错误：缺少 rules 数组"]
    return data, []


def find_rule(ledger: dict[str, Any], title: str) -> dict[str, Any] | None:
    for rule in ledger.get("rules", []):
        names = [rule.get("title", ""), *rule.get("aliases", [])]
        if title in names:
            return rule
    return None


def find_article(rule: dict[str, Any], article: str) -> str | None:
    for item in rule.get("articles", []):
        if item.get("article") == article:
            return item.get("text")
    return None


def audit_sources(text: str, ledger: dict[str, Any] | None, final: bool) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    cited = [m.groupdict() for m in CITATION_RE.finditer(text) if any(h in m.group("title") for h in RULE_TITLE_HINTS)]
    if cited and ledger is None:
        (errors if final else warnings).append("正文存在法规引用，但未提供法律依据核验台账")
        return errors, warnings
    if ledger is None:
        return errors, warnings

    opinion_date = ledger.get("opinion_date")
    if final:
        try:
            date.fromisoformat(opinion_date)
        except (TypeError, ValueError):
            errors.append("签发审计的法律依据核验台账必须填写有效的 opinion_date")

    checked: set[tuple[str, str]] = set()
    for item in cited:
        key = (item["title"], item["article"])
        if key in checked:
            continue
        checked.add(key)
        rule = find_rule(ledger, item["title"])
        if rule is None:
            (errors if final else warnings).append(f"法规未进入核验台账：《{item['title']}》{item['article']}")
            continue
        if rule.get("status") not in {"现行有效", "有效"}:
            errors.append(f"法规效力状态未确认为现行有效：《{item['title']}》")
        if rule.get("source_type") not in {"pkulaw", "yuandian", "official"}:
            errors.append(f"法规来源不是法宝、元典或发布机关官网：《{item['title']}》")
        if not rule.get("source_locator"):
            errors.append(f"法规缺少可追溯来源：《{item['title']}》")
        elif rule.get("source_type") == "official":
            parsed = urlparse(rule["source_locator"])
            host = (parsed.hostname or "").lower()
            official_host = any(host == domain or host.endswith(f".{domain}") for domain in OFFICIAL_BASE_DOMAINS)
            if parsed.scheme not in {"http", "https"} or not official_host:
                errors.append(f"标记为官网的来源不是可识别的发布机关域名：《{item['title']}》")
        try:
            verified_on = date.fromisoformat(rule.get("verified_on"))
            if final and opinion_date:
                issued_on = date.fromisoformat(opinion_date)
                if verified_on > issued_on:
                    errors.append(f"法规核验日晚于法律意见书出具日：《{item['title']}》")
                elif verified_on != issued_on:
                    errors.append(f"签发稿未在法律意见书出具日复核法规效力：《{item['title']}》")
        except (TypeError, ValueError):
            (errors if final else warnings).append(f"法规缺少有效核验日期：《{item['title']}》")
        if find_article(rule, item["article"]) is None:
            (errors if final else warnings).append(f"核验台账缺少所引条文原文：《{item['title']}》{item['article']}")

    for match in VERBATIM_RE.finditer(text):
        title, article, quote = match.group("title"), match.group("article"), match.group("quote")
        if not any(h in title for h in RULE_TITLE_HINTS):
            continue
        rule = find_rule(ledger, title)
        source_text = find_article(rule, article) if rule else None
        if source_text and normalize_verbatim(quote) not in normalize_verbatim(source_text):
            errors.append(f"标示为原文的引文与核验文本不一致：《{title}》{article}")

    return errors, warnings


def audit(
    text: str,
    flags: dict[str, Any],
    final: bool,
    source_ledger: dict[str, Any] | None = None,
) -> dict[str, list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    for section in REQUIRED_SECTIONS:
        if section not in text:
            errors.append(f"缺少必要章节或锚点：{section}")

    if "国有股东" in text and "国有股东标识" not in text:
        errors.append("正文涉及国有股东，但缺少国有股东标识分析")

    if "上市公司国有股权管理信息系统" in text:
        for anchor in ["统一编号", "股份变动情况"]:
            if anchor not in text:
                warnings.append(f"管理信息系统分析可能缺少：{anchor}")

    if "新增股份登记" in text:
        if "中国结算北京分公司" not in text:
            errors.append("新增股份登记未直接引用或分析中国结算北京分公司")
        if "目标公司" not in text and "发行人" not in text:
            warnings.append("新增股份登记未明确由发行人申请办理")

    for label, pattern in HIGH_RISK_PATTERNS.items():
        if re.search(pattern, text, re.S):
            errors.append(f"发现高风险旧模板表述：{label}")

    if "同意注册" in text and re.search(r"尚处于.{0,20}审核阶段|尚需.{0,30}北交所审核", text):
        errors.append("正文同时使用审核注册完成后的拟制口径和仍待审核口径，时点冲突")

    comment_anchors = flags.get("comment_anchors", [])
    for item in APPROVAL_SENSITIVE_PLACEHOLDERS:
        if item not in text:
            continue
        matching = [entry for entry in comment_anchors if item in entry.get("anchor", "")]
        if not matching:
            errors.append(f"审核注册占位符未被 Word 批注范围准确覆盖：{item}")
        elif not any(
            "待" in entry.get("comment", "")
            and any(word in entry.get("comment", "") for word in ("核对", "核验", "更新", "填写"))
            for entry in matching
        ):
            errors.append(f"审核注册占位符的批注未说明待核验或更新事项：{item}")

    conclusion_match = re.search(r"结论意见(?P<body>[\s\S]+?)(?:以下无正文|签署页|$)", text)
    if conclusion_match:
        body = conclusion_match.group("body")
        nums = [int(n) for n in re.findall(r"[（(](\d+)[）)]", body)]
        if nums:
            expected = list(range(1, max(nums) + 1))
            if nums != expected:
                errors.append(f"结论序号不连续或重复：{nums}")
        if re.search(r"[（(]\d+[）)]\s*(?:[（(]\d+[）)]|$)", body, re.M):
            errors.append("结论存在空序号")

        body_before_conclusion = text[: conclusion_match.start()]
        express_opinions = "\n".join(
            paragraph for paragraph in body_before_conclusion.splitlines() if "本所律师认为" in paragraph
        )
        for topic, anchors in CONCLUSION_TOPICS.items():
            if any(anchor in express_opinions for anchor in anchors) and not any(anchor in body for anchor in anchors):
                (errors if final else warnings).append(f"正文已发表意见但结论未覆盖相应主题：{topic}")
    else:
        errors.append("无法定位结论意见正文")

    placeholders: list[str] = []
    for pattern in PLACEHOLDER_PATTERNS:
        placeholders.extend(re.findall(pattern, text))
    if placeholders:
        message = "仍有占位符或待确认项：" + "、".join(dict.fromkeys(placeholders[:20]))
        (errors if final else warnings).append(message)

    if flags.get("tracked_changes"):
        (errors if final else warnings).append("DOCX仍含修订标记")
    if flags.get("comments"):
        (errors if final else warnings).append("DOCX仍含批注")

    source_errors, source_warnings = audit_sources(text, source_ledger, final)
    errors.extend(source_errors)
    warnings.extend(source_warnings)

    return {"errors": errors, "warnings": warnings}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--final", action="store_true", help="Treat warnings that block signature as errors")
    parser.add_argument("--sources", type=Path, help="JSON ledger of verified legal sources and article text")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of text")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"文件不存在：{args.input}", file=sys.stderr)
        return 2

    text, flags = read_input(args.input)
    source_ledger, ledger_errors = load_source_ledger(args.sources)
    result = audit(text, flags, args.final, source_ledger)
    result["errors"] = ledger_errors + result["errors"]
    result["file"] = [str(args.input)]

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"审计文件：{args.input}")
        for label in ("errors", "warnings"):
            print(f"{label}: {len(result[label])}")
            for item in result[label]:
                print(f"- {item}")

    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
