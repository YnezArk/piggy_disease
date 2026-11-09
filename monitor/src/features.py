# -*- coding: utf-8 -*-
"""
特征提取（设计文档 3.3 节）：
  MFCC（13 维） + 一阶差分 ΔMFCC（13 维） + 二阶差分 Δ²MFCC（13 维） = 39 维
  每段语音 -> (时间帧数, 39) 特征矩阵，统一填充/截断到固定帧数 N_FRAMES。
"""
from __future__ import annotations

import numpy as np
import librosa

import config


def extract_mfcc(y, sr=config.SAMPLE_RATE, n_mfcc=config.N_MFCC,
                 n_fft=config.N_FFT, hop_length=config.HOP_LENGTH,
                 win_length=config.WIN_LENGTH, n_mels=config.N_MELS,
                 fmax=None):
    """提取 MFCC，返回 (时间帧数, n_mfcc) 的矩阵（帧在行方向）。

    fmax: 梅尔滤波器的最高频率（Hz）。默认 None = 取奈奎斯特频率；
          若数据带宽有限（例如 8kHz 采样、有效带宽 0~4kHz），建议显式设为 4000，
          避免大量梅尔滤波器落在没有信号的频段上。
    """
    mfcc = librosa.feature.mfcc(
        y=y, sr=sr, n_mfcc=n_mfcc, n_fft=n_fft,
        hop_length=hop_length, win_length=win_length,
        n_mels=n_mels, window=config.WINDOW, fmax=fmax,
    )
    return mfcc.T.astype(np.float32)   # (T, n_mfcc)


def add_deltas(mfcc_tf, use_delta=config.USE_DELTA, use_delta2=config.USE_DELTA2):
    """拼接 MFCC + ΔMFCC + Δ²MFCC，返回 (T, F)。"""
    feats = [mfcc_tf]
    if use_delta:
        feats.append(librosa.feature.delta(mfcc_tf.T).T)
    if use_delta2:
        feats.append(librosa.feature.delta(mfcc_tf.T, order=2).T)
    return np.concatenate(feats, axis=1).astype(np.float32)


def pad_or_truncate(feat, n_frames=config.N_FRAMES):
    """把 (T, F) 特征矩阵统一到固定帧数（不足补零，超出截断）。"""
    t, f = feat.shape
    if t >= n_frames:
        return feat[:n_frames]
    pad = np.zeros((n_frames - t, f), dtype=np.float32)
    return np.concatenate([feat, pad], axis=0)


def extract_feature_matrix(y, sr=config.SAMPLE_RATE,
                           n_frames=config.N_FRAMES,
                           with_delta=True, with_delta2=True):
    """从（预处理后的）一段语音提取固定尺寸特征矩阵 (n_frames, n_features)。

    注意：调用前应保证 y 已经过预处理（带通滤波 + 预加重）并按需截断/填充。
    """
    mfcc = extract_mfcc(y, sr=sr)
    feat = add_deltas(mfcc, use_delta=with_delta, use_delta2=with_delta2)
    return pad_or_truncate(feat, n_frames)


def full_feature_pipeline(y, sr=config.SAMPLE_RATE,
                          segment_sec=config.SEGMENT_SEC,
                          n_frames=config.N_FRAMES):
    """直接从原始音频到特征矩阵（推理用，与训练预处理保持一致）：
    带通滤波(100~2000Hz) -> 预加重(0.97) -> 固定长度 -> MFCC(13)+Δ+Δ² -> 固定帧数。
    """
    from .preprocess import bandpass_filter, pre_emphasis
    y = bandpass_filter(y, sr=sr)
    y = pre_emphasis(y)
    n = int(segment_sec * sr)
    if len(y) > n:
        y = y[:n]
    elif len(y) < n:
        y = np.pad(y, (0, n - len(y)))
    return extract_feature_matrix(y, sr=sr, n_frames=n_frames)
# ---------------------------------------------------------------------------
# 特征标准化（DL 训练前拟合，推理/评估使用同一套参数）
# ---------------------------------------------------------------------------
def compute_scaler(X):
    """按特征维计算 mean/std。X: (N, T, F) -> (mean(F,), std(F,))"""
    X = np.asarray(X, dtype=np.float32)
    mean = X.mean(axis=(0, 1))
    std = X.std(axis=(0, 1)) + 1e-6
    return mean, std


def apply_scaler(X, mean, std):
    """标准化：X: (N, T, F) -> (X - mean) / std"""
    X = np.asarray(X, dtype=np.float32)
    return (X - mean) / std
