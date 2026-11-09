# -*- coding: utf-8 -*-
"""
数据增强（设计文档 3.5 节）：
  时间拉伸、音高偏移、叠加噪声、时间平移 —— 全部在波形域进行，之后再做特征提取。
"""
from __future__ import annotations

import numpy as np
import librosa

import config


def time_stretch(y, rate):
    """时间拉伸（不改变音高）。rate>1 变快（变短），rate<1 变慢（变长）。"""
    return librosa.effects.time_stretch(y, rate=rate)


def pitch_shift(y, sr, n_steps):
    """音高偏移，n_steps 为半音数（正为升高）。"""
    return librosa.effects.pitch_shift(y, sr=sr, n_steps=n_steps)


def add_noise(y, snr_db):
    """叠加高斯白噪声，使信噪比约为 snr_db dB。"""
    signal_power = np.mean(y ** 2)
    noise_power = signal_power / (10 ** (snr_db / 10.0))
    noise = np.random.randn(len(y)).astype(np.float32) * np.sqrt(noise_power)
    return y + noise


def time_shift(y, max_shift_ratio=0.2, sr=config.SAMPLE_RATE):
    """时间平移：随机裁剪/补零模拟不同起止位置。"""
    max_shift = int(max_shift_ratio * sr)
    shift = np.random.randint(-max_shift, max_shift + 1)
    if shift > 0:
        y = np.concatenate([np.zeros(shift, dtype=np.float32), y[:-shift]])
    elif shift < 0:
        y = np.concatenate([y[-shift:], np.zeros(-shift, dtype=np.float32)])
    return y


def augment_waveform(y, sr=config.SAMPLE_RATE, seed=None):
    """随机应用一组增强，返回增强后的波形（原始 + 若干副本）。"""
    if seed is not None:
        np.random.seed(seed)

    variants = [y]
    n = config.AUGMENT_TIMES
    for _ in range(n):
        v = y.copy()
        # 时间拉伸
        rate = np.random.uniform(*config.TIME_STRETCH_RANGE)
        v = time_stretch(v, rate)
        # 音高偏移
        if np.random.rand() < 0.7:
            steps = int(np.random.uniform(*config.PITCH_SHIFT_RANGE))
            if steps != 0:
                v = pitch_shift(v, sr=sr, n_steps=steps)
        # 叠加噪声
        if np.random.rand() < 0.7:
            snr = np.random.uniform(*config.NOISE_SNR_DB)
            v = add_noise(v, snr)
        # 时间平移
        if np.random.rand() < 0.5:
            v = time_shift(v, sr=sr)
        variants.append(v)
    return variants


def augment_feature_matrix(feat, n_variants=config.AUGMENT_TIMES, seed=None):
    """特征域增强（轻量）：对特征矩阵加噪声，作为波形域增强的补充/备选。"""
    if seed is not None:
        np.random.seed(seed)
    outs = [feat]
    for _ in range(n_variants):
        noise = np.random.randn(*feat.shape).astype(np.float32) * 0.02
        outs.append(feat + noise)
    return outs
