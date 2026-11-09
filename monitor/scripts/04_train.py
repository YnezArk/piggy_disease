# -*- coding: utf-8 -*-
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # 项目根目录加入模块搜索路径
"""
04_train.py —— 步骤4：训练 CNN-BiLSTM 模型
    读取 dataset_split.npz -> 训练(Adam lr=0.001, batch=32, EarlyStopping) -> 保存 best_model.h5
    可选：--cv 在"训练+验证"合并集上做五折交叉验证
运行：python scripts/04_train.py            # 常规训练
     python scripts/04_train.py --cv        # 五折交叉验证
"""

import argparse

import config
from src.dataset import load_split
from src.train import train_once, run_cv


def main(args):
    X_train, y_train, X_val, y_val, X_test, y_test = load_split()
    print(f"训练 {len(y_train)} / 验证 {len(y_val)} / 测试 {len(y_test)}")

    if args.cv:
        # 五折交叉验证：在 训练+验证 合并集上做（付小朋等做法）
        import numpy as np
        X_all = np.concatenate([X_train, X_val])
        y_all = np.concatenate([y_train, y_val])
        run_cv(X_all, y_all, n_folds=config.CV_FOLDS, seed=config.SEED)
    else:
        train_once(X_train, y_train, X_val, y_val,
                   X_test, y_test,
                   model_path=config.MODEL_DIR / "best_model.h5",
                   tag="model", save_scaler=True)
        print("训练完成，模型已保存:", config.MODEL_DIR / "best_model.h5")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cv", action="store_true", help="执行五折交叉验证")
    main(parser.parse_args())
