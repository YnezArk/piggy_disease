# -*- coding: utf-8 -*-
"""
数据集构建：
  1. 读取样本清单：优先从数据库(audio_sample)读，连不上则回退本地 data/raw/<类别> 扫描
  2. 预处理（带通滤波+预加重+端点检测）切成有效段
  3. 每段提取 MFCC(+Δ+Δ²) 39 维，统一固定帧数
  4. 可选波形域数据增强
  5. 划分：数据库已有 dataset_split 则直接用；否则按样本ID做 8:1:1 分层划分（避免同一样本泄漏）
"""
from __future__ import annotations

import random
from pathlib import Path

import numpy as np
from sklearn.model_selection import train_test_split, StratifiedKFold

import config


# ---------------------------------------------------------------------------
# 样本清单
# ---------------------------------------------------------------------------
def scan_local_samples(raw_dir=config.RAW_DIR):
    """扫描本地 data/raw/{cough,non_cough}，返回 [dict(id=None, path, label, cls_name, ...)]。"""
    raw_dir = Path(raw_dir)
    samples = []
    for cls_name in config.CLASS_NAMES:
        cls_dir = raw_dir / cls_name
        if not cls_dir.exists():
            continue
        label = config.CLASS_NAMES.index(cls_name)
        for p in sorted(cls_dir.iterdir()):
            if p.suffix.lower() in (".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac", ".wma"):
                samples.append({
                    "id": None, "path": p, "label": label, "cls_name": cls_name,
                    "sample_type": 1 if label == 0 else 0,
                    "audio_filename": p.name, "relative_path": None, "split": 0, "exists": True,
                })
    return samples


def scan_samples(use_db=None, raw_dir=config.RAW_DIR):
    """统一样本扫描：数据库优先，失败回退本地目录。

    Returns
    -------
    list[dict] : {id, path, label, cls_name, sample_type, audio_filename,
                  relative_path, split, exists}
    """
    if use_db is None:
        use_db = config.DB_ENABLED
    if use_db:
        try:
            from src.db import scan_db_samples
            samples = scan_db_samples(only_existing=True)
            if samples:
                print(f"[data] 从数据库读取 {len(samples)} 个样本（audio_sample）")
                return samples
            print("[warn] 数据库连接成功但未匹配到本地文件，回退本地扫描")
        except Exception as e:
            print(f"[warn] 数据库读取失败({type(e).__name__}: {e})，回退本地目录扫描")
    return scan_local_samples(raw_dir)


def scan_raw_files(raw_dir=config.RAW_DIR):
    """兼容旧接口：返回 [(path, label_index, class_name), ...]。"""
    return [(str(s["path"]), s["label"], s["cls_name"]) for s in scan_local_samples(raw_dir)]


# ---------------------------------------------------------------------------
# 片段处理 / 特征构建
# ---------------------------------------------------------------------------
def _to_fixed_length_segments(segments, segment_sec=config.SEGMENT_SEC,
                              sr=config.SAMPLE_RATE, max_segments=4):
    """把端点检测得到的多个片段统一为固定长度片段（截断/补零）。"""
    n = int(segment_sec * sr)
    outs = []
    for seg in segments[:max_segments]:
        if len(seg) >= n:
            outs.append(seg[:n])
        else:
            outs.append(np.pad(seg, (0, n - len(seg))))
    return outs


def process_one_audio(path, sr=config.SAMPLE_RATE, augment=config.AUGMENT):
    """单个音频 -> [(feat_matrix, None), ...]（可能含增强副本）。"""
    from src.audio_io import load_audio
    from src.preprocess import extract_voice_segments
    from src.features import extract_feature_matrix
    from src.augmentation import augment_waveform

    y, _ = load_audio(path, sr=sr)
    segs = extract_voice_segments(y, sr=sr)
    if not segs:
        segs = _to_fixed_length_segments([y], sr=sr)
        if not segs:
            return []
    fixed = _to_fixed_length_segments(segs, sr=sr)

    results = []
    for seg in fixed:
        results.append((extract_feature_matrix(seg, sr=sr), None))
    if augment:
        for seg in fixed:
            for v in augment_waveform(seg, sr=sr)[1:]:
                results.append((extract_feature_matrix(v, sr=sr), None))
    return results


def build_feature_dataset(raw_dir=config.RAW_DIR, sr=config.SAMPLE_RATE,
                          augment=config.AUGMENT, save=True, use_db=None):
    """构建完整特征数据集（可保存 npz）。

    Returns
    -------
    (X, y, names, sample_ids)
      sample_ids : 与 X 行对应的数据库样本ID（本地扫描为 -1）
    """
    samples = scan_samples(use_db=use_db, raw_dir=raw_dir)
    if not samples:
        raise FileNotFoundError(
            f"未找到任何音频样本。请确认：\n"
            f"  1) 数据库可用（config.DB_* 配置正确）或\n"
            f"  2) 本地 {raw_dir}/cough 和 {raw_dir}/non_cough 目录存在音频\n"
        )
    X, y, names, sample_ids = [], [], [], []
    for s in samples:
        try:
            for feat, _ in process_one_audio(str(s["path"]), sr=sr, augment=augment):
                X.append(feat)
                y.append(s["label"])
                names.append(str(s["audio_filename"] or Path(s["path"]).name))
                sample_ids.append(-1 if s["id"] is None else int(s["id"]))
        except Exception as e:
            print(f"[warn] 处理失败跳过 {s['path']}: {e}")
    X = np.asarray(X, dtype=np.float32)
    y = np.asarray(y, dtype=np.int64)
    sample_ids = np.asarray(sample_ids, dtype=np.int64)
    if save:
        config.FEATURE_DIR.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(config.FEATURE_DIR / "features.npz",
                            X=X, y=y, names=np.array(names), sample_ids=sample_ids)
        print(f"特征数据集已保存: {config.FEATURE_DIR / 'features.npz'}  "
              f"共 {len(y)} 个样本 (咳嗽 {int((y==0).sum())} / 非咳嗽 {int((y==1).sum())})")
    return X, y, names, sample_ids


# ---------------------------------------------------------------------------
# 划分
# ---------------------------------------------------------------------------
def split_dataset(X, y, val_ratio=0.1, test_ratio=0.1, seed=config.SEED,
                  stratify=True):
    """按行 8:1:1 分层划分（旧接口，无样本ID时使用）。"""
    strat = y if stratify else None
    X_trval, X_test, y_trval, y_test, i_trval, i_test = train_test_split(
        X, y, np.arange(len(y)), test_size=test_ratio,
        random_state=seed, stratify=strat)
    strat = y_trval if stratify else None
    X_train, X_val, y_train, y_val, i_train, i_val = train_test_split(
        X_trval, y_trval, i_trval, test_size=val_ratio / (1 - test_ratio),
        random_state=seed, stratify=strat)
    return (X_train, X_val, X_test, y_train, y_val, y_test,
            (i_train, i_val, i_test))


def split_by_sample_ids(X, y, sample_ids, val_ratio=0.1, test_ratio=0.1,
                        seed=config.SEED):
    """按样本ID粒度 8:1:1 分层划分，同一样本的所有行归入同一集合（防数据泄漏）。

    Returns
    -------
    (X_train, X_val, X_test, y_train, y_val, y_test, (i_train, i_val, i_test))
    """
    uniq, inv = np.unique(sample_ids, return_inverse=True)
    # 每个唯一样本ID的类别（取该样本第一行的标签）
    first_row = np.array([np.where(inv == k)[0][0] for k in range(len(uniq))])
    y_sample = y[first_row]

    trval_sid, te_sid, trval_y, te_y = train_test_split(
        uniq, y_sample, test_size=test_ratio, random_state=seed, stratify=y_sample)
    tr_sid, va_sid, tr_y, va_y = train_test_split(
        trval_sid, trval_y, test_size=val_ratio / (1 - test_ratio),
        random_state=seed, stratify=trval_y)

    i_train = np.where(np.isin(sample_ids, tr_sid))[0]
    i_val = np.where(np.isin(sample_ids, va_sid))[0]
    i_test = np.where(np.isin(sample_ids, te_sid))[0]
    return (X[i_train], X[i_val], X[i_test],
            y[i_train], y[i_val], y[i_test],
            (i_train, i_val, i_test))


def split_from_db_split(sample_ids, id_to_split):
    """按数据库 dataset_split(1/2/3) 生成行索引划分。

    Parameters
    ----------
    sample_ids : np.ndarray  与特征行对应的样本ID
    id_to_split : dict {sample_id: split}
    """
    i_train = np.where([id_to_split.get(int(sid), 0) == 1 for sid in sample_ids])[0]
    i_val = np.where([id_to_split.get(int(sid), 0) == 2 for sid in sample_ids])[0]
    i_test = np.where([id_to_split.get(int(sid), 0) == 3 for sid in sample_ids])[0]
    return i_train, i_val, i_test


def save_split(X, y, idx, path=None, sample_ids=None):
    """把划分结果保存到 npz，供训练/评估脚本读取。"""
    path = path or (config.FEATURE_DIR / "dataset_split.npz")
    i_train, i_val, i_test = idx
    kw = dict(X_train=X[i_train], y_train=y[i_train],
              X_val=X[i_val], y_val=y[i_val],
              X_test=X[i_test], y_test=y[i_test],
              idx_train=i_train, idx_val=i_val, idx_test=i_test)
    if sample_ids is not None:
        kw["sample_ids"] = np.asarray(sample_ids, dtype=np.int64)
    np.savez_compressed(path, **kw)
    print(f"数据集划分已保存: {path}")
    return path


def load_split(path=None):
    """读取划分后的数据集。"""
    path = path or (config.FEATURE_DIR / "dataset_split.npz")
    d = np.load(path)
    return (d["X_train"], d["y_train"], d["X_val"], d["y_val"],
            d["X_test"], d["y_test"])


def stratified_kfold_indices(y, n_folds=config.CV_FOLDS, seed=config.SEED):
    """五折交叉验证的索引生成器（训练+验证合并集上做）。"""
    skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=seed)
    return list(skf.split(np.zeros(len(y)), y))