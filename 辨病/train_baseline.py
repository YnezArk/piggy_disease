# -*- coding: utf-8 -*-
"""
辨病模块 — Step 0 快速体检 + Step 1 SVM Baseline（仅 5 类有标注疾病）

评估协议：
  A. 5 折分层交叉验证（train+val 178 条）→ 主协议 Macro-F1 ± std
  B. 固定划分（train 158 → val 20）→ 与路线文档 §4.3 验收对照
  C. 最终模型（train+val 178 全量重训）→ test 20 条独立评估（最终报告口径）

用法：
  python train_baseline.py          # 全流程
"""
import os
import json
import numpy as np
import pymysql
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import (accuracy_score, classification_report,
                             confusion_matrix, f1_score, precision_recall_fscore_support)
import joblib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FEAT_DIR = os.path.join(BASE_DIR, "features")
MODEL_DIR = os.path.join(BASE_DIR, "models")
LABEL_NAMES = ["normal", "influenza", "prrs", "mycoplasma", "app"]
DISEASE_NAMES = ["健康猪只", "猪流行性感冒", "猪蓝耳病", "猪支原体肺炎", "猪传染性胸膜肺炎"]
DB_CONFIG = dict(host="localhost", user="root", password="36987412",
                 database="pig_diag_v2", charset="utf8mb4")


def load_npz(name):
    d = np.load(os.path.join(FEAT_DIR, f"features_{name}.npz"))
    return d["X"], d["y"], d["file_id"]


def report(title, y_true, y_pred, y_proba=None):
    print(f"\n{'='*60}\n{title}\n{'='*60}")
    acc = accuracy_score(y_true, y_pred)
    macro_f1 = f1_score(y_true, y_pred, average="macro")
    print(f"Accuracy: {acc:.4f} | Macro-F1: {macro_f1:.4f}")
    print(classification_report(y_true, y_pred, target_names=LABEL_NAMES, digits=4,
                                zero_division=0))
    cm = confusion_matrix(y_true, y_pred)
    print("混淆矩阵 (行=真实, 列=预测):")
    print("        " + "  ".join(f"{n[:6]:>6}" for n in LABEL_NAMES))
    for i, row in enumerate(cm):
        print(f"{LABEL_NAMES[i][:8]:>8} " + "  ".join(f"{v:6d}" for v in row))
    # 健康类召回（误报容忍关键指标）
    p, r, f, _ = precision_recall_fscore_support(y_true, y_pred, average=None, zero_division=0)
    return dict(acc=float(acc), macro_f1=float(macro_f1),
                per_class_recall={n: float(ri) for n, ri in zip(LABEL_NAMES, r)})


def cv_eval(model, X, y, n_splits=5):
    """5 折分层 CV → (macro_f1_mean, macro_f1_std, acc_mean)"""
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    f1s, accs = [], []
    for tr, te in skf.split(X, y):
        model.fit(X[tr], y[tr])
        pred = model.predict(X[te])
        f1s.append(f1_score(y[te], pred, average="macro"))
        accs.append(accuracy_score(y[te], pred))
    return np.mean(f1s), np.std(f1s), np.mean(accs)


def main():
    os.makedirs(MODEL_DIR, exist_ok=True)
    X_tr, y_tr, _ = load_npz("train")
    X_va, y_va, _ = load_npz("val")
    X_te, y_te, te_fids = load_npz("test")
    X_cv = np.vstack([X_tr, X_va])      # 5 折 CV 用 178 条
    y_cv = np.concatenate([y_tr, y_va])
    print(f"train {X_tr.shape} / val {X_va.shape} / test {X_te.shape} / CV {X_cv.shape}")

    # ── Step 0: 快速体检（LR / RF / SVM RBF）──
    print("\n【Step 0】5 折分层 CV 快速体检 (train+val 178 条)")
    quick = {
        "LR": Pipeline([("sc", StandardScaler()),
                        ("clf", LogisticRegression(max_iter=2000, random_state=42))]),
        "RF": RandomForestClassifier(n_estimators=200, random_state=42),
        "SVM": Pipeline([("sc", StandardScaler()),
                         ("clf", SVC(kernel="rbf", C=100, gamma=0.01, probability=True))]),
    }
    step0 = {}
    for name, model in quick.items():
        mf, sd, acc = cv_eval(model, X_cv, y_cv)
        step0[name] = mf
        print(f"  {name:5s}: Macro-F1 = {mf:.4f} ± {sd:.4f} | Acc = {acc:.4f}")

    # ── Step 1: SVM Baseline（手册 §3.1 参数）──
    print("\n【Step 1】SVM RBF Baseline")
    svm = Pipeline([("sc", StandardScaler()),
                    ("clf", SVC(kernel="rbf", C=100, gamma=0.01, probability=True, random_state=42))])
    mf, sd, acc = cv_eval(svm, X_cv, y_cv)
    print(f"  5 折 CV: Macro-F1 = {mf:.4f} ± {sd:.4f} | Acc = {acc:.4f}")

    svm.fit(X_tr, y_tr)
    va_metrics = report("固定划分评估 (train 158 → val 20)", y_va, svm.predict(X_va))

    svm.fit(X_cv, y_cv)   # 全量重训
    te_metrics = report("最终模型评估 (train+val 178 → test 20)", y_te, svm.predict(X_te))

    joblib.dump(svm, os.path.join(MODEL_DIR, "svm_baseline.joblib"))
    print(f"\n模型已保存: models/svm_baseline.joblib")

    # ── model_version 落库 ──
    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT model_id FROM model_version WHERE model_name=%s AND version=%s",
                ("辨病_SVM_Baseline", "v1"))
    perf = {
        "cv5_macro_f1": round(mf, 4), "cv5_acc": round(acc, 4),
        "test_macro_f1": round(te_metrics["macro_f1"], 4),
        "test_acc": round(te_metrics["acc"], 4),
        "test_per_class_recall": {k: round(v, 4) for k, v in te_metrics["per_class_recall"].items()},
    }
    if cur.fetchone():
        cur.execute("UPDATE model_version SET performance_metrics=%s, is_active=1 WHERE model_name=%s AND version=%s",
                    (json.dumps(perf, ensure_ascii=False), "辨病_SVM_Baseline", "v1"))
    else:
        cur.execute("""
            INSERT INTO model_version (model_name, version, model_type, description,
                training_dataset_desc, hyperparameters, performance_metrics, model_path, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, ("辨病_SVM_Baseline", "v1", "诊断",
              "SVM RBF (C=100, γ=0.01) + StandardScaler，84 维均值池化特征",
              "辨病_8_1_1_v1 (train158/val20/test20, 5类)",
              json.dumps({"kernel": "rbf", "C": 100, "gamma": 0.01}),
              json.dumps(perf, ensure_ascii=False),
              "辨病/models/svm_baseline.joblib", 1))
    conn.commit()
    cur.execute("UPDATE model_version SET is_active=0 WHERE model_name='辨病_SVM_Baseline' AND version<>'v1'")
    conn.commit()
    conn.close()
    print("model_version 已落库")

    print("\n【Step 0 小结】", step0)
    print("验收对照 (达标线: Macro-F1 ≥0.75 / 健康类召回 ≥0.95):")
    print(f"  Macro-F1 = {te_metrics['macro_f1']:.4f} | 健康类召回 = {te_metrics['per_class_recall']['normal']:.4f}")


if __name__ == "__main__":
    main()
