# -*- coding: utf-8 -*-
"""
训练流程：
  - 单次训练：训练/验证/测试 8:1:1，EarlyStopping + ModelCheckpoint + ReduceLROnPlateau
  - 五折交叉验证：在 训练+验证 合并集上 5 折，评估模型稳定性（付小朋等）
  - 输出：模型权重 h5 / 训练曲线图 / 指标 json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import tensorflow as tf

import config
from src.model import build_and_compile, add_channel
from src.evaluate import compute_metrics, plot_confusion_matrix, plot_history


def _make_callbacks(model_path, patience=config.EARLY_STOPPING_PATIENCE,
                    reduce_patience=config.REDUCE_LR_PATIENCE):
    return [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss", patience=patience,
            restore_best_weights=True, verbose=1),
        tf.keras.callbacks.ModelCheckpoint(
            str(model_path), monitor="val_loss", save_best_only=True, verbose=1),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss", factor=0.5, patience=reduce_patience,
            min_lr=1e-6, verbose=1),
    ]


def _class_weights(y_train):
    """类别不平衡权重：少数类权重更高。"""
    cls, counts = np.unique(y_train, return_counts=True)
    total = len(y_train)
    return {int(c): total / (len(cls) * int(n)) for c, n in zip(cls, counts)}


def train_once(X_train, y_train, X_val, y_val, X_test=None, y_test=None,
               model_path=None, tag="run", seed=config.SEED, save_scaler=False):
    """训练一个模型并在（可选的）测试集上评估。

    Returns
    -------
    dict: 训练历史 + 测试指标（X_test 为 None 时不含指标）
    """
    tf.keras.utils.set_random_seed(seed)
    np.random.seed(seed)

    # 特征标准化：只在训练集上拟合，避免数据泄漏
    from src.features import compute_scaler, apply_scaler
    mean, std = compute_scaler(X_train)
    X_train = apply_scaler(X_train, mean, std)
    X_val = apply_scaler(X_val, mean, std)
    if X_test is not None:
        X_test = apply_scaler(X_test, mean, std)
    if save_scaler:
        config.MODEL_DIR.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(config.MODEL_DIR / "feature_scaler.npz", mean=mean, std=std)
        print("特征标准化参数已保存: models/feature_scaler.npz")

    X_train, X_val = add_channel(X_train), add_channel(X_val)
    model = build_and_compile()
    model.summary()

    model_path = model_path or (config.MODEL_DIR / f"best_{tag}.h5")
    callbacks = _make_callbacks(model_path)
    cw = _class_weights(y_train) if config.USE_CLASS_WEIGHT else None
    if cw:
        print("class weights:", cw)

    history = model.fit(
        X_train, y_train,
        batch_size=config.BATCH_SIZE,
        epochs=config.EPOCHS,
        validation_data=(X_val, y_val),
        callbacks=callbacks,
        class_weight=cw,
        verbose=1,
    )

    if Path(model_path).exists():
        model.load_weights(model_path)

    plot_history(history.history, tag=tag, save=True)

    result = {"tag": tag, "history": history.history}
    if X_test is not None:
        metrics = evaluate_test(model, X_test, y_test, tag=tag)
        result.update(metrics)
    return result


def evaluate_test(model, X_test, y_test, tag="run"):
    """在测试集上计算指标并出混淆矩阵图。"""
    X_test = add_channel(X_test)
    y_pred = np.argmax(model.predict(X_test, verbose=0), axis=1)
    metrics = compute_metrics(y_test, y_pred)
    print(f"[{tag}] test metrics: {metrics}")
    fig = plot_confusion_matrix(y_test, y_pred,
                                classes=config.CLASS_NAMES,
                                title=f"Confusion Matrix ({tag})")
    fig.savefig(config.RESULT_DIR / f"confusion_{tag}.png", dpi=150, bbox_inches="tight")
    import matplotlib.pyplot as plt
    plt.close(fig)
    return metrics


def run_cv(X, y, n_folds=config.CV_FOLDS, seed=config.SEED):
    """五折交叉验证（在 训练+验证 合并集上），每折用当折验证集评估。

    Returns
    -------
    dict: {"mean": {...}, "std": {...}}
    """
    from src.dataset import stratified_kfold_indices

    folds = stratified_kfold_indices(y, n_folds=n_folds, seed=seed)
    rows = []
    for fold, (tr_idx, va_idx) in enumerate(folds, 1):
        print(f"\n===== Fold {fold}/{n_folds} =====")
        tag = f"cv_fold{fold}"
        res = train_once(X[tr_idx], y[tr_idx], X[va_idx], y[va_idx],
                         X_test=X[va_idx], y_test=y[va_idx],
                         model_path=config.MODEL_DIR / f"cv_{tag}.h5",
                         tag=tag, seed=seed + fold)
        rows.append({"fold": fold,
                     "accuracy": res.get("accuracy"),
                     "precision": res.get("precision"),
                     "recall": res.get("recall"),
                     "f1": res.get("f1")})

    mean = {k: float(np.nanmean([r[k] for r in rows])) for k in ("accuracy", "precision", "recall", "f1")}
    std = {k: float(np.nanstd([r[k] for r in rows])) for k in ("accuracy", "precision", "recall", "f1")}
    print("\n===== 5-fold CV summary =====")
    for k in mean:
        print(f"{k}: {mean[k]*100:.2f}% ± {std[k]*100:.2f}%")

    out = config.RESULT_DIR / "cv_summary.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"rows": rows, "summary": {"mean": mean, "std": std}},
                  f, ensure_ascii=False, indent=2)
    print("CV 结果已保存:", out)
    return {"mean": mean, "std": std}
