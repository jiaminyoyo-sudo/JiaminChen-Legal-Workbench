#!/usr/bin/env python3
"""Copy the immutable Dentons template into a matter-specific working DOCX."""

from __future__ import annotations

import argparse
import re
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path

from docx import Document


SKILL_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = SKILL_ROOT / "assets" / "templates" / "大成成都_北交所定增投资方法律意见书_脱敏模板.docx"
NAME_RE = re.compile(r"_DC_\d{8}\.docx$")
CST = timezone(timedelta(hours=8))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="Absolute or relative output DOCX path")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing output file")
    args = parser.parse_args()

    output = args.output.expanduser().resolve()
    if output == TEMPLATE.resolve():
        parser.error("不得覆盖模板资产原件")
    if output.suffix.lower() != ".docx":
        parser.error("输出文件必须为 .docx")
    if not NAME_RE.search(output.name):
        parser.error("文件名必须以 _DC_YYYYMMDD.docx 结尾")
    if output.exists() and not args.force:
        parser.error(f"输出文件已存在：{output}；确需覆盖时添加 --force")

    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(TEMPLATE, output)

    doc = Document(output)
    now = datetime.now(CST)
    doc.core_properties.author = "大成律师"
    doc.core_properties.last_modified_by = "大成律师"
    doc.core_properties.created = now
    doc.core_properties.modified = now
    doc.save(output)

    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
