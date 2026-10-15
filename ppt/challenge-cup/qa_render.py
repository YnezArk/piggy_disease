# -*- coding: utf-8 -*-
"""qa_render.py — ① 修补中文字体(<a:ea>) ② 用本机 PowerPoint 渲染幻灯片为 PNG"""
import os
import re
import sys
import shutil
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
DECK = os.path.join(HERE, "猪咳嗽智能诊疗-挑战杯.pptx")
PREVIEW = os.path.join(HERE, "preview")

# ── ① 字体修补 ───────────────────────────────────────────
tmp = DECK + ".tmp"
with zipfile.ZipFile(DECK, "r") as zin:
    names = zin.namelist()
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for n in names:
            data = zin.read(n)
            if re.match(r"ppt/slides/slide\d+\.xml$", n) or n == "ppt/presentation.xml":
                xml = data.decode("utf-8")
                if "<a:ea " not in xml:
                    xml = re.sub(
                        r'(<a:latin typeface="([^"]+)"\s*/>)(?!<a:ea)',
                        r'\1<a:ea typeface="\2"/>', xml)
                data = xml.encode("utf-8")
            zout.writestr(n, data)
shutil.move(tmp, DECK)
print("[1/2] font patch done")

# ── ② PowerPoint COM 渲染 ────────────────────────────────
import win32com.client  # noqa: E402

if os.path.isdir(PREVIEW):
    for f in os.listdir(PREVIEW):
        try:
            os.remove(os.path.join(PREVIEW, f))
        except OSError:
            pass
os.makedirs(PREVIEW, exist_ok=True)

app = win32com.client.Dispatch("PowerPoint.Application")
try:
    pres = app.Presentations.Open(DECK, ReadOnly=True, WithWindow=False)
    pres.Export(PREVIEW, "PNG", 1920, 1080)
    n = pres.Slides.Count
    pres.Close()
    print(f"[2/2] exported {n} slides -> {PREVIEW}")
finally:
    app.Quit()

for f in sorted(os.listdir(PREVIEW)):
    print(" ", f, os.path.getsize(os.path.join(PREVIEW, f)) // 1024, "KB")
