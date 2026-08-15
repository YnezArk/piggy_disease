# -*- coding: utf-8 -*-
"""
辨病模块 — Step 2 主方案 SSLRB（SVM-Stacking + LR-Bagging + ROS 上采样）

架构（纪楠 2023，适配 5 类有标注疾病）：
  第一层 SVM-Stacking: 3 个 SVM 基分类器（RBF, C=100, γ∈{0.1,0.01,0.001}）
                       3 折分层 CV 生成 out-of-fold 概率 → 元特征 (3×5=15 维)
  第二层 LR-Bagging:   M=3 个逻辑回归元学习器（不同随机种子）
                       每层训练时对元特征做 ROS 随机上采样（各类均衡至最大类）
                       集成 = 3 个 LR 概率均值

评估协议与 train_baseline.py 一致：5 折 CV / 固定划分 / test 独立评估。

用法：
  python train_sslr.py
"""
import os
import json
import numpy as np
import pymysql
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import (accuracy_score, classification_report, f1_score,
                             confusion_matrix, precision_recall_fscore_support)
import joblib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FEAT_DIR = os.path.join(BASE_DIR, "features")
MODEL_DIR = os.path.join(BASE_DIR, "models")
LABEL_NAMES = ["normal", "influenza", "prrs", "mycoplasma", "app"]
DB_CONFIG = dict(host="localhost", user="root", password="36987412",
                 database="pig_diag_v2", charset="utf8mb4")

SVMS = [dict(C=100, gamma=0.1), dict(C=100, gamma=0.01), dict(C=100, gamma=0.001)]
N_LR = 3
N_CLS = len(LABEL_NAMES)


def load_npz(name):
    d = np.load(os.path.join(FEAT_DIR, f"features_{name}.npz"))
    return d["X"], d["y"], d["file_id"]


def ros_oversample(X, y):
    """随机上采样：各类样本数均衡至最大类（仅训练集使用）。"""
    counts = np.bincount(y, minlength=N_CLS)
    target = counts.max()
    xs, ys = [X], [y]
    for c in range(N_CLS):
        if counts[c] < target:
            idx = np.where(y == c)[0]
            extra = np.random.choice(idx, size=target - counts[c], replace=True)
            xs.append(X[extra]); ys.append(y[extra])
    return np.vstack(xs), np.concatenate(ys)


def stack_meta(X, y, n_splits=3, seed=42):
    """第一层：3 个 SVM 的 out-of-fold 概率 → 元特征 (N, 3*K)。"""
    meta = np.zeros((len(y), len(SVMS) * N_CLS))
    for i, params in enumerate(SVMS):
        skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
        oof = np.zeros((len(y), N_CLS))
        for tr, te in skf.split(X, y):
            sc = StandardScaler().fit(X[tr])
            svm = SVC(kernel="rbf", probability=True, random_state=seed, **params)
            svm.fit(sc.transform(X[tr]), y[tr])
            oof[te] = svm.predict_proba(sc.transform(X[te]))
        meta[:, i * N_CLS:(i + 1) * N_CLS] = oof
    return meta


def fit_predict_proba(X_tr, y_tr, X_te):
    """第二层：LR-Bagging + ROS，返回测试集概率均值。"""
    meta_tr = stack_meta(X_tr, y_tr)
    probs = []
    for i in range(N_LR):
        rng = np.random.RandomState(42 + i)
        Xr, yr = ros_oversample(meta_tr, y_tr)   # 每次 Bagging 独立上采样
        lr = LogisticRegression(max_iter=2000, random_state=42 + i)
        lr.fit(Xr, yr)
        probs.append(lr.predict_proba(_stack_on_fitted(X_tr, y_tr, X_te)))
    return np.mean(probs, axis=0)


def _stack_on_fitted(X_tr, y_tr, X_te):
    """用全量训练集拟合的 3 个 SVM 生成测试集元特征（第二层推理用）。"""
    meta = np.zeros((len(X_te), len(SVMS) * N_CLS))
    for i, params in enumerate(SVMS):
        sc = StandardScaler().fit(X_tr)
        svm = SVC(kernel="rbf", probability=True, random_state=42, **params)
        svm.fit(sc.transform(X_tr), y_tr)
        meta[:, i * N_CLS:(i + 1) * N_CLS] = svm.predict_proba(sc.transform(X_te))
    return meta


def cv_eval(X, y, n_splits=5, seed=42):
    """5 折分层 CV（外层），每折内跑完整 SSLRB。"""
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    f1s, accs = [], []
    for tr, te in skf.split(X, y):
        proba = fit_predict_proba(X[tr], y[tr], X[te])
        f1s.append(f1_score(y[te], proba.argmax(1), average="macro"))
        accs.append(accuracy_score(y[te], proba.argmax(1)))
    return np.mean(f1s), np.std(f1s), np.mean(accs)


def report(title, y_true, y_proba):
    y_pred = y_proba.argmax(1)
    print(f"\n{'='*60}\n{title}\n{'='*60}")
    print(f"Accuracy: {accuracy_score(y_true, y_pred):.4f} | Macro-F1: {f1_score(y_true, y_pred, average='macro'):.4f}")
    print(classification_report(y_true, y_pred, target_names=LABEL_NAMES, digits=4, zero_division=0))
    cm = confusion_matrix(y_true, y_pred)
    print("混淆矩阵 (行=真实, 列=预测):")
    print("        " + "  ".join(f"{n[:6]:>6}" for n in LABEL_NAMES))
    for i, row in enumerate(cm):
        print(f"{LABEL_NAMES[i][:8]:>8} " + "  ".join(f"{v:6d}" for v in row))
    p, r, f, _ = precision_recall_fscore_support(y_true, y_pred, average=None, zero_division=0)
    return dict(acc=float(accuracy_score(y_true, y_pred)),
                macro_f1=float(f1_score(y_true, y_pred, average="macro")),
                per_class_recall={n: float(ri) for n, ri in zip(LABEL_NAMES, r)})


def main():
    X_tr, y_tr, _ = load_npz("train")
    X_va, y_va, _ = load_npz("val")
    X_te, y_te, _ = load_npz("test")
    X_cv, y_cv = np.vstack([X_tr, X_va]), np.concatenate([y_tr, y_va])
    print(f"train {X_tr.shape} / val {X_va.shape} / test {X_te.shape} / CV {X_cv.shape}")

    print("\n【Step 2 SSLRB】5 折分层 CV (train+val 269 条)")
    mf, sd, acc = cv_eval(X_cv, y_cv)
    print(f"  Macro-F1 = {mf:.4f} ± {sd:.4f} | Acc = {acc:.4f}")

    # 固定划分
    va_metrics = report("固定划分评估 (train 239 → val 30)", y_va, fit_predict_proba(X_tr, y_tr, X_va))
    # 最终模型
    te_metrics = report("最终模型评估 (train+val 269 → test 30)", y_te, fit_predict_proba(X_cv, y_cv, X_te))

    # 保存最终模型（第二层 LR 权重 + 第一层 3 个 SVM）
    meta_tr = stack_meta(X_cv, y_cv)
    lrs = []
    for i in range(N_LR):
        Xr, yr = ros_oversample(meta_tr, y_cv)
        lr = LogisticRegression(max_iter=2000, random_state=42 + i).fit(Xr, yr)
        lrs.append(lr)
    svms = []
    for params in SVMS:
        sc = StandardScaler().fit(X_cv)
        svm = SVC(kernel="rbf", probability=True, random_state=42, **params).fit(sc.transform(X_cv), y_cv)
        svms.append((sc, svm))
    joblib.dump({"svms": svms, "lrs": lrs, "label_names": LABEL_NAMES},
                os.path.join(MODEL_DIR, "sslr.joblib"))
    print(f"\n模型已保存: models/sslr.joblib")

    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor()
    perf = {
        "cv5_macro_f1": round(mf, 4), "cv5_acc": round(acc, 4),
        "test_macro_f1": round(te_metrics["macro_f1"], 4),
        "test_acc": round(te_metrics["acc"], 4),
        "test_per_class_recall": {k: round(v, 4) for k, v in te_metrics["per_class_recall"].items()},
    }
    cur.execute("""
        INSERT INTO model_version (model_name, version, model_type, description,
            training_dataset_desc, hyperparameters, performance_metrics, model_path, is_active)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE performance_metrics=%s, is_active=1
    """, ("辨病_SSLRB", "v2", "诊断",
          "SVM-Stacking(3×RBF C=100 γ∈{0.1,0.01,0.001}) + LR-Bagging(3) + ROS，84维特征",
          "辨病_8_1_1_v2 (train239/val30/test30, 5类)",
          json.dumps({"svm": [p for p in SVMS], "lr": N_LR, "ros": "max-class"}),
          json.dumps(perf, ensure_ascii=False),
          "辨病/models/sslr.joblib", 1,
          json.dumps(perf, ensure_ascii=False)))
    conn.commit()
    cur.execute("UPDATE model_version SET is_active=0 WHERE model_name='辨病_SSLRB' AND version<>'v2'")
    conn.commit()
    conn.close()
    print("model_version 已落库")

    print("\n【验收对照】达标线: Macro-F1 ≥0.75 / 健康类召回 ≥0.95")
    print(f"  Macro-F1 = {te_metrics['macro_f1']:.4f} | 健康类召回 = {te_metrics['per_class_recall']['normal']:.4f}")


if __name__ == "__main__":
    main()
