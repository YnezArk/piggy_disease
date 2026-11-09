# -*- coding: utf-8 -*-
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # 项目根目录加入模块搜索路径
"""
06_predict_long_audio.py —— 步骤6：长音频/实时流式滑窗检测
    对一段长时间录音做滑窗检测，输出咳嗽事件列表 JSON。
运行：python scripts/06_predict_long_audio.py --audio 路径/音频.wav
"""

import argparse

import config
from src.inference import load_model, predict_and_save_json


def main(args):
    model = load_model()
    result = predict_and_save_json(model, args.audio,
                                   out_path=config.RESULT_DIR / "detection_result.json")
    print(f"音频时长: {result['duration_sec']} s, 检测到咳嗽事件: {result['cough_count']} 个")
    for ev in result["events"]:
        print(f"  [{ev['start_sec']:.2f}s - {ev['end_sec']:.2f}s] confidence={ev['confidence']:.3f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", required=True, help="音频文件路径")
    main(parser.parse_args())
