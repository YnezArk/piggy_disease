# -*- coding: utf-8 -*-
"""
推理：
  - 单段音频分类：返回 咳嗽/非咳嗽 概率
  - 长音频滑窗检测：把长时间录音切成固定窗口，逐窗分类，
    输出咳嗽事件列表（起始/结束时间 + 置信度），并按冷却时间合并相邻事件。
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import tensorflow as tf

import config
from src.audio_io import load_audio
from src.features import full_feature_pipeline, extract_feature_matrix
from src.preprocess import preprocess_segment


def load_model(path=None):
    """加载训练好的模型（默认 models/best_model.h5）。"""
    path = path or (config.MODEL_DIR / "best_model.h5")
    if not Path(path).exists():
        raise FileNotFoundError(f"模型不存在: {path}，请先运行 scripts/04_train.py")
    return tf.keras.models.load_model(str(path))


_scaler_cache = None


def load_feature_scaler(path=None):
    """加载训练时保存的特征标准化参数 (mean, std)；不存在返回 None（兼容旧模型）。"""
    global _scaler_cache
    if _scaler_cache is not None:
        return _scaler_cache
    path = path or (config.MODEL_DIR / "feature_scaler.npz")
    if not Path(path).exists():
        _scaler_cache = None
        return None
    d = np.load(path)
    _scaler_cache = (d["mean"], d["std"])
    return _scaler_cache


def predict_segment(model, y, sr=config.SAMPLE_RATE):
    """预测单段（已预处理）音频 -> (prob_cough, prob_non_cough)。

    Parameters
    ----------
    y : np.ndarray
        原始（未预处理）波形，函数内部自动做预加重与固定长度
    """
    feat = full_feature_pipeline(y, sr=sr)                     # (T, F)
    scaler = load_feature_scaler()
    if scaler is not None:
        mean, std = scaler
        feat = (feat - mean) / std
    feat = feat[None, ..., None]                               # (1, T, F, 1)
    prob = model.predict(feat, verbose=0)[0]
    return float(prob[0]), float(prob[1])


def predict_audio_file(model, path, sr=config.SAMPLE_RATE):
    """预测整个音频文件 -> (prob_cough, prob_non_cough)。"""
    y, _ = load_audio(path, sr=sr)
    return predict_segment(model, y, sr=sr)


def predict_long_audio(model, path, sr=config.SAMPLE_RATE,
                       window_sec=config.WINDOW_SEC, hop_sec=config.HOP_SEC,
                       conf_threshold=config.CONFIDENCE_THRESHOLD,
                       cooldown_sec=config.COOLDOWN_SEC):
    """长音频滑窗检测咳嗽事件。

    Returns
    -------
    dict: {
      "path": str,
      "duration_sec": float,
      "events": [{"start_sec", "end_sec", "confidence", "label"}, ...],
      "cough_count": int
    }
    """
    y, _ = load_audio(path, sr=sr)
    duration = len(y) / sr
    hop = int(hop_sec * sr)
    win = int(window_sec * sr)

    events = []
    # 与训练一致：先在预处理信号上做端点检测找有效段，取原始波形段逐段判定
    # （固定滑窗会从文件开头切，长录音里的咳嗽经常被切丢/截断）
    from src.preprocess import bandpass_filter, pre_emphasis, energy_endpoint_detect
    yb = pre_emphasis(bandpass_filter(y, sr=sr))
    segs = energy_endpoint_detect(yb, sr=sr)

    if segs:
        for s, e in segs:
            seg = y[s:e]
            p_cough, _ = predict_segment(model, seg, sr=sr)
            if p_cough >= conf_threshold:
                events.append({
                    "start_sec": round(s / sr, 2),
                    "end_sec": round(e / sr, 2),
                    "confidence": round(p_cough, 4),
                    "label": "cough",
                })
    else:
        # 无有效段（如很安静的文件）：整段/滑窗兜底
        if len(y) < win:
            starts = [0]
        else:
            starts = range(0, len(y) - win + 1, hop)
        for start in starts:
            seg = y[start:start + win]
            p_cough, _ = predict_segment(model, seg, sr=sr)
            if p_cough >= conf_threshold:
                events.append({
                    "start_sec": round(start / sr, 2),
                    "end_sec": round((start + win) / sr, 2),
                    "confidence": round(p_cough, 4),
                    "label": "cough",
                })

    # 合并冷却时间内的相邻事件（同一声咳嗽可能跨多个窗口）
    merged = []
    for ev in events:
        if merged and ev["start_sec"] - merged[-1]["end_sec"] <= cooldown_sec:
            prev = merged[-1]
            prev["end_sec"] = max(prev["end_sec"], ev["end_sec"])
            prev["confidence"] = max(prev["confidence"], ev["confidence"])
        else:
            merged.append(dict(ev))

    return {
        "path": str(path),
        "duration_sec": round(duration, 2),
        "events": merged,
        "cough_count": len(merged),
    }


def predict_and_save_json(model, path, out_path=None, **kwargs):
    """长音频检测并保存 JSON（设计文档 3.8 节输出格式）。"""
    result = predict_long_audio(model, path, **kwargs)
    out_path = out_path or (config.RESULT_DIR / "detection_result.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("检测结果已保存:", out_path)
    return result
