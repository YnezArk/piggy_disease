# -*- coding: utf-8 -*-
"""
音频读写与基础处理：
- 用 soundfile 读取（避免 librosa.load 对部分 MP3 调用 ffmpeg 导致的卡顿）
- 统一重采样、转单声道、保存 wav
"""
from __future__ import annotations

import numpy as np
import soundfile as sf
import librosa

import config


def load_audio(path, sr=config.SAMPLE_RATE, mono=True):
    """读取音频文件，统一采样率与声道。

    Parameters
    ----------
    path : str
        音频文件路径（wav/mp3/flac 等 soundfile 支持的格式）
    sr : int
        目标采样率，None 表示保持原采样率
    mono : bool
        是否转为单声道（多声道取平均）

    Returns
    -------
    y : np.ndarray, shape (n_samples,)
        音频信号，归一化到 [-1, 1] 附近
    sr : int
        实际采样率
    """
    y, orig_sr = sf.read(path, dtype="float32", always_2d=False)
    if y.ndim > 1:
        if mono:
            y = y.mean(axis=1)   # 多声道 -> 单声道
        else:
            y = y.reshape(-1, 1)

    if sr is not None and orig_sr != sr:
        y = resample(y, orig_sr, sr)

    return y.astype(np.float32), (sr if sr is not None else orig_sr)


def resample(y, orig_sr, target_sr):
    """重采样（librosa 纯 numpy 实现，不依赖外部解码器）。"""
    if orig_sr == target_sr:
        return y
    return librosa.resample(y, orig_sr=orig_sr, target_sr=target_sr).astype(np.float32)


def to_mono(y):
    if y.ndim > 1:
        return y.mean(axis=1)
    return y


def save_wav(path, y, sr=config.SAMPLE_RATE):
    """保存为 wav（16bit PCM）。"""
    path = str(path)
    sf.write(path, y.astype(np.float32), sr, subtype="PCM_16")
    return path


def read_chunks(path, chunk_sec=5.0, sr=config.SAMPLE_RATE):
    """按块读取大音频，供长音频流式处理使用（内存友好）。

    Returns
    -------
    generator of (y_chunk, start_sample)
    """
    import soundfile as sf
    y, orig_sr = load_audio(path, sr=sr)
    n = int(chunk_sec * sr)
    for start in range(0, len(y), n):
        yield y[start:start + n], start
