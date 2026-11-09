# -*- coding: utf-8 -*-
"""
15_md2docx.py —— 把 Markdown 转成 Word（.docx）
支持：标题/表格/代码块/无序列表/有序列表/引用/加粗/行内代码/分割线
用法: python scripts\15_md2docx.py <input.md> [output.docx]
"""
import sys, io, re, pathlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

CN_FONT = "微软雅黑"
CODE_FONT = "Consolas"


def set_font(run, name=CN_FONT, size=None, bold=None, italic=None, color=None):
    run.font.name = name
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts"); rPr.append(rFonts)
    rFonts.set(qn("w:eastAsia"), name)
    rFonts.set(qn("w:ascii"), name)
    rFonts.set(qn("w:hAnsi"), name)
    if size: run.font.size = Pt(size)
    if bold is not None: run.bold = bold
    if italic is not None: run.italic = italic
    if color: run.font.color.rgb = color


def shade(el, fill="F2F2F2"):
    """给段落/单元格加底纹"""
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), fill)
    el.append(shd)


def add_inline(par, text, base_size=10.5, base_bold=False):
    """处理 **加粗** 与 `行内代码`"""
    for tk in re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", text):
        if not tk:
            continue
        if tk.startswith("**") and tk.endswith("**"):
            r = par.add_run(tk[2:-2]); set_font(r, size=base_size, bold=True)
        elif tk.startswith("`") and tk.endswith("`"):
            r = par.add_run(tk[1:-1]); set_font(r, CODE_FONT, size=base_size - 0.5)
            r.font.color.rgb = RGBColor(0xC0, 0x39, 0x2B)
        else:
            r = par.add_run(tk); set_font(r, size=base_size, bold=base_bold)


def add_code_block(doc, lines):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(4); p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.left_indent = Inches(0.15)
    shade(p._p.get_or_add_pPr(), "F5F5F5")
    for i, ln in enumerate(lines):
        if i: p.add_run().add_break()
        r = p.add_run(ln if ln else " ")
        set_font(r, CODE_FONT, size=9)


def add_table(doc, header, rows):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]; c.text = ""
        par = c.paragraphs[0]; add_inline(par, h, base_size=9.5, base_bold=True)
        shade(c._tc.get_or_add_tcPr(), "DEEAF6")
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row[:len(header)]):
            cells[i].text = ""
            add_inline(cells[i].paragraphs[0], v, base_size=9.5)
    return t


def convert(md_path, out_path):
    lines = pathlib.Path(md_path).read_text(encoding="utf-8").split("\n")
    doc = Document()
    # 默认字体
    st = doc.styles["Normal"]
    st.font.name = CN_FONT; st.font.size = Pt(10.5)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), CN_FONT)

    i = 0
    n = len(lines)
    while i < n:
        ln = lines[i].rstrip()
        # 代码块
        if ln.strip().startswith("```"):
            block = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                block.append(lines[i].rstrip()); i += 1
            i += 1
            add_code_block(doc, block)
            continue
        # 表格
        if ln.strip().startswith("|") and i + 1 < n and re.match(r"^\s*\|[\s:\-|]+\|\s*$", lines[i + 1]):
            header = [c.strip() for c in ln.strip().strip("|").split("|")]
            i += 2
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            add_table(doc, header, rows)
            doc.add_paragraph()
            continue
        # 标题
        m = re.match(r"^(#{1,4})\s+(.*)$", ln)
        if m:
            level = len(m.group(1))
            h = doc.add_heading(level=min(level, 4))
            add_inline(h, m.group(2), base_size={1: 18, 2: 15, 3: 13, 4: 11.5}[level], base_bold=True)
            for r in h.runs:
                set_font(r, size={1: 18, 2: 15, 3: 13, 4: 11.5}[level], bold=True, color=RGBColor(0x1F, 0x3B, 0x73))
            i += 1
            continue
        # 分割线
        if re.match(r"^\s*-{3,}\s*$", ln):
            i += 1
            continue
        # 引用
        if ln.strip().startswith(">"):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.25)
            add_inline(p, ln.strip().lstrip("> ").strip(), base_size=10)
            for r in p.runs: r.italic = True
            i += 1
            continue
        # 无序列表
        m = re.match(r"^\s*[-*]\s+(.*)$", ln)
        if m:
            p = doc.add_paragraph(style="List Bullet")
            add_inline(p, m.group(1))
            i += 1
            continue
        # 有序列表
        m = re.match(r"^\s*(\d+)[.、]\s+(.*)$", ln)
        if m:
            p = doc.add_paragraph(style="List Number")
            add_inline(p, m.group(2))
            i += 1
            continue
        # 空行
        if not ln.strip():
            i += 1
            continue
        # 普通段落
        p = doc.add_paragraph()
        add_inline(p, ln)
        i += 1
    doc.save(out_path)
    print(f"已生成 Word: {out_path}  ({pathlib.Path(out_path).stat().st_size/1024:.1f} KB)")


if __name__ == "__main__":
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else str(pathlib.Path(src).with_suffix(".docx"))
    convert(src, dst)