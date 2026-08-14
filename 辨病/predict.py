# -*- coding: utf-8 -*-
"""
辨病模块 — 推理模块（wav → 疾病诊断）

输出契约（与论治引擎 /api/diagnosis 对齐）：
  {"label": "influenza", "disease": "猪流行性感冒", "confidence": 0.87,
   "cough_type": "湿咳", "symptoms": "自动生成的症状描述", "top3": [...]}

- 默认使用 **SVM Baseline**（models/svm_baseline.joblib，实测 test Macro-F1 0.6333 最优），
  可用 --model sslr 切 SSLRB 集成（0.5000）
- **决策口径（2026-08-14）：恒输出 5 类之一（健康 + 4 病），取置信度最高者，不做拒答**；
  猪肺疫/混合感染等无标注类别未来加数据后扩充类别，当前不做 unknown 拒绝
- confidence 供论治层辨病纠错参考，不参与拒答

用法：
  python predict.py path/to/cough.wav
"""
import os
import sys
import json
import numpy as np
import joblib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "models")
LABEL_NAMES = ["normal", "influenza", "prrs", "mycoplasma", "app"]
DISEASE_NAMES = ["健康猪只", "猪流行性感冒", "猪蓝耳病", "猪支原体肺炎", "猪传染性胸膜肺炎"]
# 注：system_config.diagnosis_threshold 保留（未来类别扩充/分级提示用），当前不参与拒答

# 症状模板（供论治层 symptoms 字段；兼症由模型 Top2 概率叠加生成）
TYPICAL_SYMPTOMS = {
    "normal": "呼吸平稳，无咳嗽，精神饱满",
    "influenza": "鹅鸣样剧咳，突发高热，全群发病",
    "prrs": "高调湿咳，渐进性加重，腹式呼吸，耳尖发紫",
    "mycoplasma": "慢性干咳，早晚加重，病程长",
    "app": "急骤痛咳，湿咳，全身重症，高致死率",
}


MODEL_FILES = {"svm": "svm_baseline.joblib", "sslr": "sslr.joblib"}


def load_model(name="svm"):
    path = os.path.join(MODEL_DIR, MODEL_FILES.get(name, name))
    if not os.path.exists(path):
        raise FileNotFoundError(f"模型不存在: {path}，请先运行 train_baseline.py 或 train_sslr.py")
    return joblib.load(path)


def predict_proba(model, X):
    """统一概率接口：SSLRB 字典结构 / SVM Pipeline 均可。"""
    if isinstance(model, dict):           # SSLRB: {"svms":[(sc,svm)...], "lrs":[...]}
        meta = np.zeros((len(X), 3 * len(LABEL_NAMES)))
        for i, (sc, svm) in enumerate(model["svms"]):
            meta[:, i * 5:(i + 1) * 5] = svm.predict_proba(sc.transform(X))
        return np.mean([lr.predict_proba(meta) for lr in model["lrs"]], axis=0)
    return model.predict_proba(X)         # sklearn Pipeline


def diagnose(wav_path, model=None, model_name="sslr"):
    """wav → 诊断结果 dict（契约见模块 docstring）。"""
    import features as F
    if model is None:
        model = load_model(model_name)
    X = np.concatenate([F.extract_features(wav_path)[k] for k in F.FEATURE_NAMES]).reshape(1, -1)
    proba = predict_proba(model, X)[0]
    top = np.argsort(proba)[::-1]
    label = LABEL_NAMES[top[0]]   # 恒输出 5 类之一，取置信度最高，不拒答

    result = {
        "label": label,
        "disease": DISEASE_NAMES[top[0]],
        "confidence": round(float(proba[top[0]]), 4),
        "cough_type": "干咳/湿咳（待监测板块补充）",
        "symptoms": TYPICAL_SYMPTOMS[label],
        "top3": [{"label": LABEL_NAMES[i], "disease": DISEASE_NAMES[i],
                  "confidence": round(float(proba[i]), 4)} for i in top[:3]],
    }
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    wav = sys.argv[1]
    name = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] in ("sslr", "svm") else "svm"
    try:
        r = diagnose(wav, model_name=name)
        print(json.dumps(r, ensure_ascii=False, indent=2))
    except FileNotFoundError as e:
        print(f"❌ {e}")
