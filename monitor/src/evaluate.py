# -*- coding: utf-8 -*-
"""
评估：准确率 / 精确率 / 召回率 / F1 / 混淆矩阵 / 训练曲线（设计文档 3.7 节）。
"""
from __future__ import annotations

import json

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, confusion_matrix, classification_report)

import config


def compute_metrics(y_true, y_pred):
    """计算二分类指标。返回 dict（百分数 *100）。"""
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, average="binary", pos_label=0)),
        "recall": float(recall_score(y_true, y_pred, average="binary", pos_label=0)),
        "f1": float(f1_score(y_true, y_pred, average="binary", pos_label=0)),
    }


def plot_confusion_matrix(y_true, y_pred, classes=None, title="Confusion Matrix",
                          normalize=True, save_path=None):
    """绘制混淆矩阵（正常化展示），返回 Figure。"""
    if classes is None:
        classes = config.CLASS_NAMES
    cm = confusion_matrix(y_true, y_pred)
    if normalize:
        cm = cm.astype(float) / (cm.sum(axis=1, keepdims=True) + 1e-9)

    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    im = ax.imshow(cm, interpolation="nearest", cmap="Blues")
    ax.figure.colorbar(im, ax=ax)
    ax.set(xticks=np.arange(len(classes)), yticks=np.arange(len(classes)),
           xticklabels=classes, yticklabels=classes,
           xlabel="Predicted", ylabel="True", title=title)
    thresh = cm.max() / 2.0
    for i in range(len(classes)):
        for j in range(len(classes)):
            ax.text(j, i, f"{cm[i, j]:.2f}",
                    ha="center", va="center",
                    color="white" if cm[i, j] > thresh else "black")
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


def plot_history(history, tag="run", save=True):
    """绘制训练/验证 loss 与 accuracy 曲线。"""
    fig, ax = plt.subplots(1, 2, figsize=(12, 4))
    ax[0].plot(history["loss"], label="train")
    ax[0].plot(history["val_loss"], label="val")
    ax[0].set_title("Loss"); ax[0].legend(); ax[0].grid(alpha=.3)
    ax[1].plot(history["accuracy"], label="train")
    ax[1].plot(history["val_accuracy"], label="val")
    ax[1].set_title("Accuracy"); ax[1].legend(); ax[1].grid(alpha=.3)
    fig.tight_layout()
    if save:
        fig.savefig(config.RESULT_DIR / f"history_{tag}.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    return fig


def report_to_json(y_true, y_pred, path=None):
    """保存分类报告与混淆矩阵到 json。"""
    rep = classification_report(y_true, y_pred, target_names=config.CLASS_NAMES,
                                output_dict=True)
    cm = confusion_matrix(y_true, y_pred).tolist()
    out = {"classification_report": rep, "confusion_matrix": cm,
           "metrics_percent": compute_metrics(y_true, y_pred)}
    path = path or (config.RESULT_DIR / "evaluation_report.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("评估报告已保存:", path)
    return out
