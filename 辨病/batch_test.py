# -*- coding: utf-8 -*-
"""
辨病模块 — 全样本批量识别测试（生成记录文档）

对 pig_cough_data 全部 wav（5 类标注 299 + unknown 2）逐个识别，
输出：
  - 全样本识别结果.csv        （301 行逐条明细）
  - 全样本识别报告.md          （总体/各类指标 + 混淆矩阵 + 误判清单）

注意：本测试包含训练数据（in-sample），指标仅供参考与样本级核查，
泛化指标以固定划分 test 30 条为准（SSLRB v2: Macro-F1 0.7933）。

用法：
  python batch_test.py [--model svm|sslr] [--out 前缀]
"""
import os
import sys
import csv
import argparse
from datetime import datetime

from bianbing_config import AUDIO_ROOT
from predict import diagnose, load_model, LABEL_NAMES

DISEASE_NAMES = ["健康猪只", "猪流行性感冒", "猪蓝耳病", "猪支原体肺炎", "猪传染性胸膜肺炎"]
GROUPS = LABEL_NAMES + ["unknown"]


def collect(model, model_name):
    rows = []
    for g in GROUPS:
        folder = os.path.join(AUDIO_ROOT, g)
        if not os.path.isdir(folder):
            continue
        for fn in sorted(f for f in os.listdir(folder) if f.lower().endswith(".wav")):
            src = f"{g}/{fn}"
            r = diagnose(os.path.join(folder, fn), model=model, model_name=model_name)
            truth = g if g in LABEL_NAMES else "unknown"
            rows.append({
                "file": src, "truth": truth, "predict": r["label"],
                "confidence": r["confidence"], "disease": r["disease"],
                "top2": r["top3"][1]["label"] if len(r["top3"]) > 1 else "",
                "hit": (truth == r["label"]) if truth != "unknown" else "?",
            })
            print(f"  {src:40s} 真实={truth:12s} 预测={r['label']:12s} conf={r['confidence']:.3f} "
                  f"{'✅' if rows[-1]['hit'] is True else ('·' if rows[-1]['hit'] == '?' else '❌')}")
    return rows


def write_csv(rows, path):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["file", "truth", "predict", "confidence", "disease", "top2", "hit"])
        w.writeheader()
        w.writerows(rows)
    print(f"CSV 已生成: {path} ({len(rows)} 行)")


def write_md(rows, path, model_name):
    labeled = [r for r in rows if r["truth"] != "unknown"]
    correct = [r for r in labeled if r["hit"] is True]
    acc = len(correct) / len(labeled) if labeled else 0

    # 各类别指标
    lines = [f"# 辨病模型全样本识别测试报告",
             f"",
             f"> **日期**：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
             f"> **模型**：{model_name}（v2，train 239/val 30/test 30）",
             f"> **数据**：{len(rows)} 条（标注 {len(labeled)} + unknown {len(rows)-len(labeled)}）",
             f"> **性质**：全样本回测（**含训练数据，in-sample**），供样本级核查；泛化指标以固定划分 test 30 条为准（Macro-F1 0.7933）",
             f"",
             f"## 一、总体指标（in-sample）",
             f"",
             f"| 指标 | 值 |",
             f"|------|----|",
             f"| 标注样本数 | {len(labeled)} |",
             f"| 识别正确 | {len(correct)} |",
             f"| **准确率** | **{acc:.4f}** |",
             f"",
             f"## 二、各类别指标",
             f"",
             f"| 类别 | 样本 | 正确 | 准确率 |",
             f"|------|------|------|--------|"]
    for g in LABEL_NAMES:
        sub = [r for r in labeled if r["truth"] == g]
        ok = [r for r in sub if r["hit"] is True]
        lines.append(f"| {g} | {len(sub)} | {len(ok)} | {len(ok)/len(sub):.4f} |")

    # 混淆矩阵
    lines += ["", "## 三、混淆矩阵（行=真实, 列=预测）", "",
              "| 真实\\预测 | " + " | ".join(LABEL_NAMES + ["其他"]) + " |",
              "|---------|" + "|".join(["---"] * (len(LABEL_NAMES) + 1)) + "|"]
    for g in LABEL_NAMES:
        row = [g]
        for p in LABEL_NAMES:
            row.append(str(sum(1 for r in rows if r["truth"] == g and r["predict"] == p)))
        row.append(str(sum(1 for r in rows if r["truth"] == g and r["predict"] not in LABEL_NAMES)))
        lines.append("| " + " | ".join(row) + " |")

    # 误判清单
    wrong = [r for r in labeled if r["hit"] is not True]
    lines += ["", f"## 四、误判清单（{len(wrong)} 条）", "",
              "| 文件 | 真实 | 预测 | 置信度 | 次高预测 |",
              "|------|------|------|--------|---------|"]
    for r in sorted(wrong, key=lambda x: (x["truth"], x["file"])):
        lines.append(f"| {r['file']} | {r['truth']} | {r['predict']} | {r['confidence']:.3f} | {r['top2']} |")

    # unknown 桶
    unk = [r for r in rows if r["truth"] == "unknown"]
    if unk:
        lines += ["", f"## 五、unknown 桶识别结果（{len(unk)} 条，未标注）", "",
                  "| 文件 | 预测 | 置信度 |", "|------|------|--------|"]
        for r in unk:
            lines.append(f"| {r['file']} | {r['predict']} | {r['confidence']:.3f} |")

    lines += ["", f"*误判样本是标签审计/数据质量核查的切入点（见辨病路线文档 §4.1 标签审计）。*"]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"报告已生成: {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="sslr", choices=["sslr", "svm"])
    ap.add_argument("--out", default="全样本识别")
    args = ap.parse_args()

    print(f"加载模型: {args.model} ...")
    model = load_model(args.model)
    print(f"开始识别 {AUDIO_ROOT} 下全部样本 ...\n")
    rows = collect(model, args.model)

    write_csv(rows, os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{args.out}结果.csv"))
    write_md(rows, os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{args.out}报告.md"), args.model)


if __name__ == "__main__":
    main()
