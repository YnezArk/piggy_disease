# -*- coding: utf-8 -*-
"""Minimal Markdown -> DOCX converter for project documents.

Supports headings, paragraphs, bullet/numbered lists, blockquotes, fenced code,
and pipe tables. Intended for Chinese project docs, not full Markdown.
"""
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt, Cm, RGBColor


def set_run_font(run, name="Microsoft YaHei", size=None, bold=None, color=None, mono=False):
    if mono:
        name = "Consolas"
    run.font.name = name
    r = run._element
    r.rPr.rFonts.set(qn("w:eastAsia"), name)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if color is not None:
        run.font.color.rgb = RGBColor(*color)


def add_inline(paragraph, text, size=10.5, base_bold=False, color=None):
    """Add text with **bold** support."""
    parts = re.split(r"(\*\*.+?\*\*)", text)
    for part in parts:
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            run = paragraph.add_run(part[2:-2])
            set_run_font(run, size=size, bold=True, color=color)
        else:
            run = paragraph.add_run(part)
            set_run_font(run, size=size, bold=base_bold, color=color)


def is_sep_row(cells):
    return all(re.fullmatch(r":?-{2,}:?", c.strip()) for c in cells if c.strip() != "")


def parse_table(lines, i):
    rows = []
    while i < len(lines) and lines[i].strip().startswith("|"):
        raw = lines[i].strip()
        cells = [c.strip() for c in raw.strip("|").split("|")]
        if not is_sep_row(cells):
            rows.append(cells)
        i += 1
    return rows, i


def main(md_path, docx_path):
    text = Path(md_path).read_text(encoding="utf-8")
    lines = text.splitlines()
    doc = Document()

    # page setup
    for section in doc.sections:
        section.top_margin = Cm(2.0)
        section.bottom_margin = Cm(2.0)
        section.left_margin = Cm(2.2)
        section.right_margin = Cm(2.2)

    # base styles
    normal = doc.styles["Normal"]
    normal.font.name = "Microsoft YaHei"
    normal.font.size = Pt(10.5)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
    normal.paragraph_format.space_after = Pt(4)
    normal.paragraph_format.line_spacing = 1.3

    for lvl in range(1, 5):
        st = doc.styles[f"Heading {lvl}"]
        st.font.name = "Microsoft YaHei"
        st.element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
        st.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)
        st.font.bold = True
        st.paragraph_format.space_before = Pt(10 if lvl <= 2 else 6)
        st.paragraph_format.space_after = Pt(4)

    i = 0
    in_code = False
    code_buf = []
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code:
                p = doc.add_paragraph()
                p.paragraph_format.left_indent = Cm(0.5)
                run = p.add_run("\n".join(code_buf))
                set_run_font(run, size=9, mono=True)
                code_buf = []
                in_code = False
            else:
                in_code = True
            i += 1
            continue
        if in_code:
            code_buf.append(line)
            i += 1
            continue

        if not stripped:
            i += 1
            continue

        if stripped == "---":
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(2)
            run = p.add_run("—" * 30)
            set_run_font(run, size=8, color=(0xAA, 0xAA, 0xAA))
            i += 1
            continue

        # table
        if stripped.startswith("|"):
            rows, i = parse_table(lines, i)
            if rows:
                ncols = max(len(r) for r in rows)
                table = doc.add_table(rows=len(rows), cols=ncols)
                table.style = "Table Grid"
                table.autofit = True
                for ri, row in enumerate(rows):
                    for ci in range(ncols):
                        cell = table.cell(ri, ci)
                        cell.text = ""
                        p = cell.paragraphs[0]
                        p.paragraph_format.space_after = Pt(1)
                        val = row[ci] if ci < len(row) else ""
                        add_inline(p, val, size=8.5, base_bold=(ri == 0))
                doc.add_paragraph()
            continue

        # heading
        m = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if m:
            level = len(m.group(1))
            p = doc.add_heading(level=level)
            add_inline(p, m.group(2), size={1: 18, 2: 14, 3: 12, 4: 11}[level], base_bold=True)
            i += 1
            continue

        # blockquote
        if stripped.startswith(">"):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.6)
            add_inline(p, stripped.lstrip("> ").strip(), size=9.5, color=(0x55, 0x55, 0x55))
            i += 1
            continue

        # bullet
        m = re.match(r"^[-*]\s+(.*)$", stripped)
        if m:
            p = doc.add_paragraph(style="List Bullet")
            add_inline(p, m.group(1))
            i += 1
            continue

        # numbered
        m = re.match(r"^\d+\.\s+(.*)$", stripped)
        if m:
            p = doc.add_paragraph(style="List Number")
            add_inline(p, m.group(1))
            i += 1
            continue

        # paragraph
        p = doc.add_paragraph()
        add_inline(p, stripped)
        i += 1

    doc.save(docx_path)
    print(f"saved: {docx_path}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
