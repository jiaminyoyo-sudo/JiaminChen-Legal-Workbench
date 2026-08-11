#!/usr/bin/env python3
"""Render a lawyer-letter DOCX while retaining the user's font environment."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--emit-pdf", action="store_true")
    parser.add_argument("--dpi", type=int, default=150)
    args = parser.parse_args()

    if not args.input.is_file():
        print(f"输入 DOCX 不存在：{args.input}", file=sys.stderr)
        return 2
    soffice = shutil.which("soffice")
    pdftoppm = shutil.which("pdftoppm")
    if not soffice or not pdftoppm:
        print("需要 soffice 和 pdftoppm", file=sys.stderr)
        return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="lawyer_letter_profile_") as profile, tempfile.TemporaryDirectory(
        prefix="lawyer_letter_pdf_"
    ) as pdf_tmp:
        command = [
            soffice,
            f"-env:UserInstallation=file://{profile}",
            "--invisible",
            "--headless",
            "--norestore",
            "--convert-to",
            "pdf",
            "--outdir",
            pdf_tmp,
            str(args.input),
        ]
        completed = subprocess.run(command, env=os.environ.copy(), capture_output=True, text=True)
        if completed.returncode:
            print(completed.stdout, file=sys.stderr)
            print(completed.stderr, file=sys.stderr)
            return completed.returncode
        pdf_path = Path(pdf_tmp) / f"{args.input.stem}.pdf"
        if not pdf_path.is_file():
            print("LibreOffice 未生成 PDF", file=sys.stderr)
            return 2
        prefix = args.output_dir / "page"
        completed = subprocess.run(
            [pdftoppm, "-png", "-r", str(args.dpi), str(pdf_path), str(prefix)],
            capture_output=True,
            text=True,
        )
        if completed.returncode:
            print(completed.stdout, file=sys.stderr)
            print(completed.stderr, file=sys.stderr)
            return completed.returncode
        if args.emit_pdf:
            shutil.copy2(pdf_path, args.output_dir / pdf_path.name)

    pages = sorted(args.output_dir.glob("page-*.png"))
    if not pages:
        print("未生成页面图片", file=sys.stderr)
        return 2
    for page in pages:
        print(page)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
