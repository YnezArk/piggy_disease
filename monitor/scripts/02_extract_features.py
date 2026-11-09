# -*- coding: utf-8 -*-
"""
02_extract_features.py —— 步骤2：特征提取
对 data/processed/{label}/ 中每个有效段提取 MFCC(13) + Δ + Δ2 = 39 维特征，
统一到固定帧数 N_FRAMES，保存为 data/features/features.npz。
若文件名带 id<样本ID>_ 前缀（01 从数据库生成时写入），则同时保存 sample_ids，
供 03 按样本ID划分（同一样本不跨训练/测试）。
运行：python scripts/02_extract_features.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import re

import numpy as np

import config
from src.audio_io import load_audio
from src.features import extract_feature_matrix

_ID_RE = re.compile(r"^id(\d+)_")


def parse_sample_id(filename):
    """从 id000123_xxx.wav 中解析样本ID，解析不到返回 -1。"""
    m = _ID_RE.match(filename)
    return int(m.group(1)) if m else -1


def main(processed_dir=config.PROCESSED_DIR, out_dir=config.FEATURE_DIR):
    X, y, names, sample_ids = [], [], [], []
    for cls_name in config.CLASS_NAMES:
        cls_dir = Path(processed_dir) / cls_name
        if not cls_dir.exists():
            print(f"[skip] 目录不存在: {cls_dir}")
            continue
        files = sorted(cls_dir.glob("*.wav"))
        print(f"[{cls_name}] 共 {len(files)} 个有效段")
        for p in files:
            try:
                sig, sr = load_audio(p)
                feats = [extract_feature_matrix(sig, sr=sr)]   # (N_FRAMES, 39)
                if config.AUGMENT_TRAIN:
                    from src.augmentation import augment_waveform
                    for v in augment_waveform(sig, sr=sr)[1:]:   # 每个样本再生成 AUGMENT_TIMES 个增强副本
                        feats.append(extract_feature_matrix(v, sr=sr))
                sid = parse_sample_id(p.name)
                for feat in feats:
                    X.append(feat)
                    y.append(config.CLASS_NAMES.index(cls_name))
                    names.append(p.name)
                    sample_ids.append(sid)
            except Exception as e:
                print(f"  [warn] {p.name}: {e}")

    X = np.asarray(X, dtype=np.float32)
    y = np.asarray(y, dtype=np.int64)
    sample_ids = np.asarray(sample_ids, dtype=np.int64)
    out_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out_dir / "features.npz",
                        X=X, y=y, names=np.array(names), sample_ids=sample_ids)
    n_db = int((sample_ids >= 0).sum())
    print(f"特征提取完成: {len(y)} 个样本, 特征形状 {X.shape[1:]}, "
          f"其中来自数据库的样本行 {n_db} -> {out_dir / 'features.npz'}")


if __name__ == "__main__":
    main()