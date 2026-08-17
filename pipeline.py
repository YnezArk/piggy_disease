# -*- coding: utf-8 -*-
"""
诊疗决策板块 — 完整流程编排（辨病 + 论治一键串联）

调用方式：
  1. Python 调用：
       from pipeline import full_pipeline
       result = full_pipeline("辨病/pig_cough_data/mycoplasma/myco_1.wav", temp_c=39.2)
  2. 命令行：
       python pipeline.py 辨病/pig_cough_data/app/app_1.wav --temp 40.1 --weight 70 --severity 重度
  3. API（见 api_server.py）：
       POST /api/diagnose-audio  (multipart: file=wav + 可选参数)

模块职责（解耦约定）：
  辨病（辨病/predict.py）  : wav → 诊断 JSON，独立可调
  论治（therapy_engine.py）: 诊断+症状 → 方案 JSON，独立可调
  桥接（辨病/bridge.py）   : 两者契约的唯一转换点
  本文件                   : 只做编排，不含业务逻辑
"""
import os
import sys
import json
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "辨病"))
from predict import diagnose, load_model
from bridge import build_therapy_input, call_therapy


def full_pipeline(wav_path, temp_c=39.0, weight_kg=70.0, severity="中度",
                  symptoms=None, pig_extra="", model_name="sslr"):
    """wav → 辨病 → 论治 → 完整报告（辨病诊断 + 辨证 + 组方 + 校验）。"""
    print("【1/3】辨病（声学分类）...")
    dx = diagnose(wav_path, model_name=model_name)
    print(f"      {dx['disease']} (label={dx['label']}, conf={dx['confidence']:.3f})")

    therapy, meta = build_therapy_input(
        dx, temp_c=temp_c, weight_kg=weight_kg, severity=severity,
        symptoms=symptoms, pig_extra=pig_extra)

    print(f"【2/3】桥接：disease={therapy['disease']} | symptoms={therapy['symptoms'][:40]}...")
    print(f"【3/3】论治（RAG+LLM 辨证组方）...")
    rx = call_therapy(therapy)

    return {"diagnosis": dx, "meta": meta, "therapy": therapy, "result": rx}


def main():
    ap = argparse.ArgumentParser(description="辨病+论治 完整流程")
    ap.add_argument("wav", help="咳嗽音频路径")
    ap.add_argument("--temp", type=float, default=39.0, help="体温℃（缺省 39.0）")
    ap.add_argument("--weight", type=float, default=70.0, help="体重kg")
    ap.add_argument("--severity", default="中度", choices=["轻度", "中度", "重度"])
    ap.add_argument("--symptoms", default=None, help="手动输入实际症状（缺省为空，不自动用辨病典型症状）")
    ap.add_argument("--pig-extra", default="", help="补充信息（月龄等）")
    ap.add_argument("--model", default="sslr", choices=["sslr", "svm"])
    args = ap.parse_args()

    if not os.path.exists(args.wav):
        print(f"❌ 文件不存在: {args.wav}")
        return 1

    try:
        full = full_pipeline(args.wav, temp_c=args.temp, weight_kg=args.weight,
                             severity=args.severity, symptoms=args.symptoms,
                             pig_extra=args.pig_extra, model_name=args.model)
    except Exception as e:
        print(f"❌ 流程失败: {e}")
        return 1

    # ── 输出完整报告 ──
    dx, rx = full["diagnosis"], full["result"]
    sx, vf = rx["syndrome"], rx["verification"]
    print("\n" + "=" * 60)
    print("  完整诊疗报告（辨病 → 辨证 → 组方 → 校验）")
    print("=" * 60)
    print(f"【辨病】{dx['disease']}  (conf={dx['confidence']:.3f}, top3={[t['label'] for t in dx['top3']]})")
    print(f"  典型症状(展示): {dx.get('typical_symptoms', '')}")
    print(f"【辨证】{sx.get('stage', '')} · {sx.get('syndrome', '')}")
    print(f"  治则: {sx.get('principle', '')}")
    print(f"  依据: {'; '.join(sx.get('evidence', []))}")
    dc = sx.get('disease_conflict') or {}
    if dc:
        print(f"  疾病对照: 辨病[{dc.get('upstream_disease', '?')}] vs 证据[{dc.get('evidence_disease', '?')}] "
              f"{'⚠️不一致' if dc.get('conflict') else '一致'}")
    print(f"【组方】{rx['prescription'].get('base_formula', '')}")
    for h in rx["prescription"].get("herbs", []):
        print(f"  {h['name']:<8}{h['dosage_g']:<8}{h.get('role', '')}")
    print(f"  用法: {rx['prescription'].get('preparation', '')} | 疗程: {rx['prescription'].get('course', '')}")
    print(f"【校验】{'✅ 通过' if vf['safe'] else '❌ 拦截'}")
    for e in vf.get("errors", []):
        print(f"  [拦截] {e}")
    for w in vf.get("warnings", []):
        print(f"  [提示] {w}")
    print("\n  ⚠️ 本结果由AI辅助生成，仅供兽医参考，用药请遵兽医指导")
    return 0


if __name__ == "__main__":
    sys.exit(main())
