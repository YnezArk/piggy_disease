# -*- coding: utf-8 -*-
"""
03_build_dataset.py —— 步骤3：构建数据集（划分训练/验证/测试）
    读取 features.npz -> 划分 -> 保存 dataset_split.npz
    划分方式（优先级）：
      1) 数据库 audio_sample.dataset_split 已设置(1/2/3) -> 直接使用
      2) 否则按样本ID做 8:1:1 分层划分（同一样本不跨集合，防泄漏）
      3) 无样本ID（本地扫描）-> 按行 8:1:1 分层划分（旧行为）
    可选把划分结果写回数据库：--write-back（或 config.DB_WRITE_SPLIT_BACK=True）
运行：python scripts/03_build_dataset.py [--write-back] [--no-db]
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse

import numpy as np

import config
from src.dataset import (split_dataset, split_by_sample_ids, split_from_db_split,
                         save_split)


def main(args):
    fp = config.FEATURE_DIR / "features.npz"
    d = np.load(fp)
    X, y = d["X"], d["y"]
    sample_ids = d["sample_ids"] if "sample_ids" in d else None
    print(f"总样本数: {len(y)}  (咳嗽 {int((y==0).sum())} / 非咳嗽 {int((y==1).sum())})")

    use_db = not args.no_db and config.DB_ENABLED
    id_to_split = None
    if use_db and sample_ids is not None and (sample_ids >= 0).any():
        from src.db import Database
        with Database() as db:
            rows = db.get_samples()
        id_to_split = {int(r["id"]): int(r["dataset_split"]) for r in rows}
        n_set = sum(1 for v in id_to_split.values() if v in (1, 2, 3))
        print(f"数据库 dataset_split 已设置 {n_set}/{len(id_to_split)} 条")
        if n_set > 0:
            # 使用数据库划分
            i_tr, i_va, i_te = split_from_db_split(sample_ids, id_to_split)
            if len(i_tr) and len(i_va) and len(i_te):
                idx = (i_tr, i_va, i_te)
                print(f"[split] 使用数据库 dataset_split: "
                      f"训练 {len(i_tr)} / 验证 {len(i_va)} / 测试 {len(i_te)}")
                save_split(X, y, idx, sample_ids=sample_ids)
                return

    if sample_ids is not None and (sample_ids >= 0).any():
        # 按样本ID 8:1:1 划分
        X_train, X_val, X_test, y_train, y_val, y_test, idx = split_by_sample_ids(
            X, y, sample_ids, val_ratio=0.1, test_ratio=0.1, seed=config.SEED)
        print(f"[split] 按样本ID 8:1:1 划分: "
              f"训练 {len(y_train)} / 验证 {len(y_val)} / 测试 {len(y_test)}")
    else:
        X_train, X_val, X_test, y_train, y_val, y_test, idx = split_dataset(
            X, y, val_ratio=0.1, test_ratio=0.1, seed=config.SEED)
        print(f"[split] 按行 8:1:1 划分: "
              f"训练 {len(y_train)} / 验证 {len(y_val)} / 测试 {len(y_test)}")
    print(f"训练集分布: 咳嗽 {int((y_train==0).sum())} / 非咳嗽 {int((y_train==1).sum())}")
    save_split(X, y, idx, sample_ids=sample_ids)

    # 写回数据库
    write_back = args.write_back or config.DB_WRITE_SPLIT_BACK
    if write_back and id_to_split is not None or (write_back and sample_ids is not None and (sample_ids >= 0).any()):
        # 每个样本ID -> 它所在集合(1/2/3)
        sid_to_split = {}
        i_tr, i_va, i_te = idx
        for i in i_tr:
            sid_to_split.setdefault(int(sample_ids[i]), 1)
        for i in i_va:
            sid_to_split.setdefault(int(sample_ids[i]), 2)
        for i in i_te:
            sid_to_split.setdefault(int(sample_ids[i]), 3)
        sid_to_split = {k: v for k, v in sid_to_split.items() if k >= 0}
        if sid_to_split:
            from src.db import Database
            with Database() as db:
                n = db.update_dataset_split(sid_to_split)
            print(f"[write-back] 已把 {n} 个样本的 dataset_split 写回数据库")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-back", action="store_true",
                        help="把划分结果写回数据库 audio_sample.dataset_split")
    parser.add_argument("--no-db", action="store_true", help="不使用数据库划分")
    main(parser.parse_args())