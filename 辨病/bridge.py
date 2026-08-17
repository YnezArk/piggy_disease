# -*- coding: utf-8 -*-
"""
辨病模块 — 桥接层（辨病输出 → 论治输入 契约转换）

解耦约定：
  - 辨病只产 JSON：{label, disease, confidence, typical_symptoms, top3}
  - 论治只收契约：treatment_pipeline(disease, symptoms, temp, weight, severity, pig_extra)
  - 本模块是唯一转换点，两端互不 import
  - **typical_symptoms 仅供显示，不输入论治**；论治的 symptoms 为手动输入的实际症状

用法：
  from bridge import build_therapy_input
  therapy_kwargs, meta = build_therapy_input(dx_result, temp_c=39.5, ...)
"""
from typing import Optional

# 论治引擎参数名（与 therapy_engine.treatment_pipeline 签名一致）
THERAPY_FIELDS = ("disease", "symptoms", "temp", "weight", "severity", "pig_extra")


def build_therapy_input(dx: dict,
                        symptoms: Optional[str] = None,
                        temp_c: float = 39.0,
                        weight_kg: float = 70.0,
                        severity: str = "中度",
                        pig_extra: str = "") -> tuple:
    """辨病诊断 JSON → 论治调用参数。

    symptoms = **手动输入的实际症状**（2026-08-16 定调：不再用辨病 typical_symptoms 兜底）；
    未提供时传空串，论治按"缺实际症状"处理（辨证依据不足会低置信度标记）。
    返回 (论治 kwargs, 附加元数据 dict)，附加元数据供落库/审计。
    """
    therapy = {
        "disease": dx["disease"],                 # 中文病名（论治契约，过别名归一）
        "symptoms": symptoms or "",               # 实际症状：仅来自手动输入
        "temp": float(temp_c),
        "weight": float(weight_kg),
        "severity": severity,
        "pig_extra": pig_extra,
    }
    meta = {
        "label": dx["label"],                     # 辨病模型标签（落库 model_label）
        "confidence": dx["confidence"],           # 置信度（落库 + 论治纠错参考）
        "cough_type": dx.get("cough_type", ""),
        "typical_symptoms": dx.get("typical_symptoms", ""),  # 仅供显示
        "top3": dx.get("top3", []),
    }
    return therapy, meta


def call_therapy(therapy_kwargs: dict, pipeline_fn=None):
    """按契约调用论治引擎（惰性 import，保持模块解耦）。"""
    if pipeline_fn is None:
        import sys, os
        ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if ROOT not in sys.path:
            sys.path.insert(0, ROOT)
        from therapy_engine import treatment_pipeline as pipeline_fn
    return pipeline_fn(**{k: therapy_kwargs[k] for k in THERAPY_FIELDS})
