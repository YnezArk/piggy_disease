# -*- coding: utf-8 -*-
"""
信号预处理（设计文档 3.2 节 / 付小朋等，2026）：
  1. 四阶巴特沃斯带通滤波（100~2000 Hz）降噪
  2. 一阶高通预加重（alpha=0.97），增强高频能量
  3. 分帧加窗（25ms / 10ms / 汉明窗）
  4. 短时能量自适应阈值端点检测：TE = mu_E + 0.5*sigma_E，提取有效语音段
"""
from __future__ import annotations

import numpy as np
from scipy.signal import butter, sosfiltfilt, lfilter

import config


# ---------------------------------------------------------------------------
# 1. 降噪：四阶巴特沃斯带通滤波器
# ---------------------------------------------------------------------------
def bandpass_filter(y, sr=config.SAMPLE_RATE,
                    low=config.BANDPASS_LOW, high=config.BANDPASS_HIGH,
                    order=config.BUTTER_ORDER):
    """四阶巴特沃斯带通滤波，保留 100~2000 Hz 能量集中频段，抑制低频/高频噪声。"""
    nyq = 0.5 * sr
    low = max(low, 1.0)
    high = min(high, nyq - 1.0)
    sos = butter(order, [low, high], btype="bandpass", fs=sr, output="sos")
    return sosfiltfilt(sos, y).astype(np.float32)


# ---------------------------------------------------------------------------
# 2. 预加重：一阶高通滤波器  H(z) = 1 - alpha * z^-1
# ---------------------------------------------------------------------------
def pre_emphasis(y, alpha=config.PRE_EMPHASIS_ALPHA):
    """补偿高频能量衰减，突出高频共振峰。"""
    return lfilter([1.0, -alpha], [1.0], y).astype(np.float32)


# ---------------------------------------------------------------------------
# 3. 分帧
# ---------------------------------------------------------------------------
def frame_signal(y, frame_len=config.WIN_LENGTH, hop=config.HOP_LENGTH):
    """分帧，返回 (n_frames, frame_len) 的数组。"""
    if len(y) < frame_len:
        y = np.pad(y, (0, frame_len - len(y)))
    n_frames = 1 + (len(y) - frame_len) // hop
    idx = np.arange(frame_len)[None, :] + hop * np.arange(n_frames)[:, None]
    return y[idx]


# ---------------------------------------------------------------------------
# 4. 端点检测：短时能量 + 自适应阈值（含间隔合并）
# ---------------------------------------------------------------------------
def energy_endpoint_detect(y, sr=config.SAMPLE_RATE,
                           frame_len=config.WIN_LENGTH, hop=config.HOP_LENGTH,
                           thresh_coef=config.STE_THRESH_COEF,
                           min_segment_sec=config.MIN_SEGMENT_SEC,
                           max_segment_sec=config.MAX_SEGMENT_SEC,
                           max_gap_frames=None):
    """基于短时能量的自适应阈值端点检测。

    算法（付小朋等）：
      帧 RMS 能量 E(n)；自适应能量阈值 TE = mu_E + 0.5*sigma_E；
      能量高于阈值的帧视为有效语音帧；
      相邻有效帧之间间隔 <= max_gap_frames 的合并为同一段（避免把一声咳嗽切碎）；
      剔除过短片段（< min_segment_sec），超过 max_segment_sec 的从起始截断。

    Returns
    -------
    list[tuple[int, int]] : (start_sample, end_sample) 列表
    """
    if max_gap_frames is None:
        max_gap_frames = max(1, int(0.15 * sr / hop))   # 默认合并 150ms 内的间隔

    frames = frame_signal(y, frame_len, hop)
    energy = np.sqrt((frames ** 2).mean(axis=1))          # 帧 RMS 能量 E(n)
    te = energy.mean() + thresh_coef * energy.std()       # 自适应阈值 TE

    active = energy > te
    # 找到所有有效帧的索引，并按间隔合并
    idx_active = np.where(active)[0]
    groups = []
    if len(idx_active) > 0:
        cur = [idx_active[0]]
        for i in idx_active[1:]:
            if i - cur[-1] <= max_gap_frames + 1:
                cur.append(i)
            else:
                groups.append(cur)
                cur = [i]
        groups.append(cur)

    min_frames = max(1, int(min_segment_sec * sr / hop))
    segments = []
    for g in groups:
        start = int(g[0] * hop)
        end = min(int((g[-1] + 1) * hop + frame_len), len(y))
        if end - start >= min_frames * hop:
            max_len = int(max_segment_sec * sr)
            if end - start > max_len:
                end = start + max_len
            segments.append((start, end))
    return segments


def preprocess_segment(y, sr=config.SAMPLE_RATE):
    """对单段语音依次做：带通滤波 -> 预加重（返回预处理后的波形）。"""
    y = bandpass_filter(y, sr=sr)
    y = pre_emphasis(y)
    return y


def extract_voice_segments(y, sr=config.SAMPLE_RATE):
    """完整预处理：带通滤波 -> 预加重 -> 端点检测，返回有效语音段列表。

    Returns
    -------
    list[np.ndarray] : 每段为预处理后的波形
    """
    y = bandpass_filter(y, sr=sr)
    y = pre_emphasis(y)
    segs = energy_endpoint_detect(y, sr=sr)
    return [y[s:e] for s, e in segs]
