# -*- coding: utf-8 -*-
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # 项目根目录加入模块搜索路径
"""
05_evaluate.py —— 步骤5：模型评估
    在测试集上计算 准确率/精确率/召回率/F1，绘制混淆矩阵并保存报告。
运行：python scripts/05_evaluate.py
"""

import config
from src.dataset import load_split
from src.inference import load_model
from src.evaluate import compute_metrics, plot_confusion_matrix, report_to_json


def main():
    X_train, y_train, X_val, y_val, X_test, y_test = load_split()
    model = load_model()
    import numpy as np
    from src.features import apply_scaler
    from src.inference import load_feature_scaler
    scaler = load_feature_scaler()
    if scaler is not None:
        X_test = apply_scaler(X_test, *scaler)
    from src.model import add_channel
    y_pred = np.argmax(model.predict(add_channel(X_test), verbose=0), axis=1)

    metrics = compute_metrics(y_test, y_pred)
    print("\n===== 测试集评估结果 =====")
    for k, v in metrics.items():
        print(f"{k}: {v*100:.2f}%")

    fig = plot_confusion_matrix(y_test, y_pred, classes=config.CLASS_NAMES,
                                title="Test Confusion Matrix",
                                save_path=config.RESULT_DIR / "confusion_test.png")
    print("混淆矩阵已保存: results/confusion_test.png")
    report_to_json(y_test, y_pred, path=config.RESULT_DIR / "evaluation_report.json")


if __name__ == "__main__":
    main()
