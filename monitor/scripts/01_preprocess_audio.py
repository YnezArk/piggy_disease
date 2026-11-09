# -*- coding: utf-8 -*-
"""
01_preprocess_audio.py —— 步骤1：信号预处理（样本清单来自数据库 audio_sample）
对数据库（或本地 data/raw）中每个音频：
    带通滤波(100~2000Hz) -> 预加重(0.97) -> 端点检测(短时能量自适应阈值)
    将切出的有效语音段保存到 data/processed/{label}/ 下
    若端点检测未切出有效段，则整段按固定长度截取作为兜底（与特征构建逻辑一致）。
运行：
    python scripts/01_preprocess_audio.py           # 默认：优先数据库，失败回退本地
    python scripts/01_preprocess_audio.py --no-db   # 强制本地目录扫描
    python scripts/01_preprocess_audio.py --split 1 # 只处理数据库里 dataset_split=1 的样本
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse

import config
from src.audio_io import load_audio, save_wav
from src.preprocess import extract_voice_segments
from src.dataset import scan_samples, _to_fixed_length_segments


def main(args):
    samples = scan_samples(use_db=None if not args.no_db else False)
    if args.split is not None:
        samples = [s for s in samples if s["split"] == args.split]
    if not samples:
        print("没有可处理的样本（清单为空）。")
        return

    total_segs = 0
    for cls_name in config.CLASS_NAMES:
        out_dir = Path(config.PROCESSED_DIR) / cls_name
        out_dir.mkdir(parents=True, exist_ok=True)
        files = [s for s in samples if s["cls_name"] == cls_name]
        if not files:
            print(f"[skip] 无 {cls_name} 类样本")
            continue
        print(f"[{cls_name}] 共 {len(files)} 个原始音频")
        for s in files:
            p = s["path"]
            try:
                y, sr = load_audio(p)
                segs = extract_voice_segments(y, sr=sr)
                if not segs:                      # 兜底：整段固定长度
                    segs = _to_fixed_length_segments([y], sr=sr)
            except Exception as e:
                print(f"  [warn] {p.name}: {e}")
                continue
            for j, seg in enumerate(segs):
                # 数据库样本：文件名带样本ID前缀，供 02 恢复 sample_id 用
                if s["id"] is not None:
                    name = f"id{s['id']:06d}_{p.stem}_{j:02d}.wav"
                else:
                    name = f"{p.stem}_{j:02d}.wav"
                save_wav(out_dir / name, seg, sr)
                total_segs += 1
    print(f"预处理完成，共切出 {total_segs} 个有效语音段 -> {config.PROCESSED_DIR}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-db", action="store_true", help="强制本地目录扫描，不连数据库")
    parser.add_argument("--split", type=int, default=None,
                        help="只处理指定 dataset_split(1/2/3) 的数据库样本")
    main(parser.parse_args())