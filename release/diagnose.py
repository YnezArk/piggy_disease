# -*- coding: utf-8 -*-
"""
diagnose.py — 辨病推理模块（wav → 疾病诊断，无训练功能）

输出契约：
  {"label": "influenza", "disease": "猪流行性感冒", "confidence": 0.87,
   "cough_type": "...", "typical_symptoms": "...", "top3": [...]}

- 特征口径与训练时完全一致：84 维（MFCC13 + logFBank64 + 时域3 + 频域4，均值池化）
- 模型：models/sslr.joblib（默认，v3 六类）或 models/svm_baseline.joblib
- 恒输出 6 类之一（健康 + 5 病），取置信度最高，不拒答
- typical_symptoms 仅供展示，不输入论治（论治实际症状由调用方手动传入）

用法：
  from diagnose import diagnose
  r = diagnose("x.wav")                     # 默认 SSLRB
  r = diagnose("x.wav", model_name="svm")
"""
import os
import numpy as np
import librosa
import joblib

from config import MODEL_DIR

LABEL_NAMES = ["normal", "influenza", "prrs", "mycoplasma", "app", "other_disease"]
DISEASE_NAMES = ["健康猪只", "猪流行性感冒", "猪蓝耳病", "猪支原体肺炎", "猪传染性胸膜肺炎", "其他疾病"]

MODEL_FILES = {"svm": "svm_baseline.joblib", "sslr": "sslr.joblib"}


# ── 疾病信息查询（典型症状等，数据源 = MySQL disease 表，不写死）─────
_meta_cache = {}  # label -> {name, symptoms}


def _load_disease_meta():
    """label → 疾病名/典型症状（DB disease 表；不可用时降级为内置名表）"""
    if _meta_cache:
        return _meta_cache
    try:
        import pymysql
        from config import DB
        conn = pymysql.connect(**DB)
        cur = conn.cursor()
        cur.execute("SELECT label, name, symptoms FROM disease WHERE label IS NOT NULL")
        for label, name, symptoms in cur.fetchall():
            _meta_cache[label] = {"name": name, "symptoms": symptoms or ""}
        conn.close()
    except Exception:
        pass  # DB 不可用 → 仅内置名表
    for label, name in zip(LABEL_NAMES, DISEASE_NAMES):
        _meta_cache.setdefault(label, {"name": name, "symptoms": ""})
    return _meta_cache

# ── 特征提取（与训练管线逐参数一致）────────────────────────
SR, DURATION, N_MFCC, N_FFT, HOP = 16000, 1.0, 13, 2048, 512


def extract_features(path):
    """单条音频 → 84 维特征（均值池化）"""
    y, sr = librosa.load(path, sr=SR, duration=DURATION)
    if len(y) < sr * DURATION:
        y = np.pad(y, (0, int(sr * DURATION) - len(y)))
    mfcc = np.mean(librosa.feature.mfcc(y=y, sr=sr, n_mfcc=N_MFCC, n_fft=N_FFT, hop_length=HOP), axis=1)
    logmel = librosa.power_to_db(
        librosa.feature.melspectrogram(y=y, sr=sr, n_mels=64, n_fft=N_FFT, hop_length=HOP), ref=np.max)
    logfbank = np.mean(logmel, axis=1)
    temporal = np.array([np.sum(y ** 2) / len(y),
                         np.mean(librosa.feature.zero_crossing_rate(y)[0]),
                         np.mean(librosa.feature.rms(y=y)[0])])
    spectral = np.array([np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)[0]),
                         np.mean(librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]),
                         np.mean(librosa.feature.spectral_flatness(y=y)[0]),
                         np.mean(librosa.feature.spectral_rolloff(y=y, sr=sr)[0])])
    return np.concatenate([mfcc, logfbank, temporal, spectral]).astype(np.float64)  # (84,)


# ── 模型加载与预测 ─────────────────────────────────────────
def load_model(name="sslr"):
    path = os.path.join(MODEL_DIR, MODEL_FILES.get(name, name))
    if not os.path.exists(path):
        raise FileNotFoundError(f"模型不存在: {path}")
    return joblib.load(path)


def predict_proba(model, X):
    """统一概率接口：SSLRB 字典结构 / sklearn Pipeline 均可"""
    if isinstance(model, dict):  # SSLRB: {"svms":[(scaler,svm)...], "lrs":[...]}
        n_cls = len(LABEL_NAMES)
        meta = np.zeros((len(X), len(model["svms"]) * n_cls))
        for i, (sc, svm) in enumerate(model["svms"]):
            meta[:, i * n_cls:(i + 1) * n_cls] = svm.predict_proba(sc.transform(X))
        return np.mean([lr.predict_proba(meta) for lr in model["lrs"]], axis=0)
    return model.predict_proba(X)


def diagnose(wav_path, model=None, model_name="sslr"):
    """wav → 诊断结果 dict（契约见模块 docstring）"""
    if model is None:
        model = load_model(model_name)
    X = extract_features(wav_path).reshape(1, -1)
    proba = predict_proba(model, X)[0]
    top = np.argsort(proba)[::-1]
    label = LABEL_NAMES[top[0]]
    meta = _load_disease_meta()
    return {
        "label": label,
        "disease": meta[label]["name"],
        "confidence": round(float(proba[top[0]]), 4),
        "cough_type": "干咳/湿咳（待监测板块补充）",
        "typical_symptoms": meta[label]["symptoms"],   # 来自 DB disease.symptoms（仅展示）
        "top3": [{"label": LABEL_NAMES[i], "disease": meta[LABEL_NAMES[i]]["name"],
                  "confidence": round(float(proba[i]), 4)} for i in top[:3]],
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    import json
    name = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] in ("sslr", "svm") else "sslr"
    print(json.dumps(diagnose(sys.argv[1], model_name=name), ensure_ascii=False, indent=2))
