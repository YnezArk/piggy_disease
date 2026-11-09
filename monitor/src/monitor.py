# -*- coding: utf-8 -*-
"""
监测与预警（设计文档 3.8 节 / 王梦雨预警系统）：
  - 实时/准实时接收音频（文件夹轮询 或 麦克风）
  - 调用模型滑窗检测咳嗽事件
  - 按时间窗统计咳嗽频次（每小时），计算健康基线
  - 阈值预警：1 小时内咳嗽次数 >= ALERT_COUGH_PER_HOUR 或较基线升高 50% -> 触发预警
  - 输出结构化 JSON，供下游诊断模块/小程序调用
"""
from __future__ import annotations

import json
import time
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

import config
from src.inference import load_model, predict_long_audio, predict_segment


class CoughMonitor:
    """猪舍咳嗽监测器：聚合事件 -> 统计 -> 预警。"""

    def __init__(self, model_path=None,
                 pig_house_id="A栋3号舍",
                 alert_per_hour=config.ALERT_COUGH_PER_HOUR,
                 ratio_baseline=config.ALERT_RATIO_BASELINE):
        self.model = load_model(model_path)
        self.pig_house_id = pig_house_id
        self.alert_per_hour = alert_per_hour
        self.ratio_baseline = ratio_baseline
        # 记录 (timestamp, count) 用于滑动小时窗口统计
        self._events = deque()
        self._baseline = None      # 健康期每小时咳嗽次数基线
        self._alert_state = "normal"

    # ---------------- 单窗预测 ----------------
    def predict_waveform(self, y, sr=config.SAMPLE_RATE):
        """对一段波形预测咳嗽概率。"""
        p_cough, _ = predict_segment(self.model, y, sr=sr)
        return p_cough

    # ---------------- 事件记录 ----------------
    def record_audio(self, audio_path):
        """处理一段音频，记录其中咳嗽事件。

        Returns
        -------
        list[dict] : 本次检测到的咳嗽事件
        """
        res = predict_long_audio(self.model, str(audio_path))
        now = datetime.now()
        for ev in res["events"]:
            self._events.append({"time": now.strftime("%H:%M:%S"),
                                 "confidence": ev["confidence"],
                                 "duration_sec": round(ev["end_sec"] - ev["start_sec"], 2)})
        # 只保留最近 24 小时（简化：按天清理）
        while len(self._events) > 86400:
            self._events.popleft()
        return res["events"]

    # ---------------- 统计与预警 ----------------
    def cough_count_in_window(self, minutes=60):
        """统计最近 minutes 分钟内的咳嗽次数（按时间排序，滑动窗口）。"""
        now = datetime.now()
        start = now - timedelta(minutes=minutes)
        n = 0
        for ev in self._events:
            t = datetime.strptime(ev["time"], "%H:%M:%S").replace(
                year=now.year, month=now.month, day=now.day)
            if start <= t <= now:
                n += 1
        return n

    def update_baseline(self, hourly_count):
        """更新健康基线（指数滑动平均，避免突发波动影响）。"""
        if self._baseline is None:
            self._baseline = float(hourly_count)
        else:
            self._baseline = 0.8 * self._baseline + 0.2 * float(hourly_count)
        return self._baseline

    def check_alert(self):
        """根据当前小时频次判断预警级别：normal / warning / critical。"""
        count = self.cough_count_in_window(60)
        if self._baseline is None:
            self.update_baseline(count)
            return "normal", count

        if count >= self.alert_per_hour:
            level = "critical" if count >= 2 * self.alert_per_hour else "warning"
        elif self._baseline > 0 and count >= self.ratio_baseline * self._baseline:
            level = "warning"
        else:
            level = "normal"
        self.update_baseline(count)
        self._alert_state = level
        return level, count

    def status_json(self):
        """输出结构化状态（设计文档 3.8 节 JSON 示例）。"""
        level, count = self.check_alert()
        now = datetime.now()
        return {
            "pig_house_id": self.pig_house_id,
            "timestamp": now.strftime("%Y-%m-%dT%H:%M:%S"),
            "cough_events": list(self._events)[-20:],
            "cough_count_hourly": count,
            "baseline_hourly": round(self._baseline, 2) if self._baseline else None,
            "alert_level": level,
        }

    def save_status(self, out_path=None):
        out_path = out_path or (config.RESULT_DIR / "monitor_status.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(self.status_json(), f, ensure_ascii=False, indent=2)
        print("监测状态已保存:", out_path)
        return out_path


def monitor_folder(folder, interval_sec=10.0, max_rounds=None,
                   pig_house_id="A栋3号舍", processed_ext=".wav"):
    """文件夹轮询监测：持续扫描 folder 中新增的音频并检测。

    适合"采集端定时落盘 -> 本模块定时拉取"的准实时场景。
    """
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    monitor = CoughMonitor(pig_house_id=pig_house_id)
    done = set()
    rounds = 0
    print(f"[monitor] 开始监测文件夹 {folder} ...")
    try:
        while max_rounds is None or rounds < max_rounds:
            for p in sorted(folder.glob(f"*{processed_ext}")):
                if p.name in done:
                    continue
                print(f"[monitor] 检测 {p.name} ...")
                monitor.record_audio(p)
                done.add(p.name)
            status = monitor.status_json()
            print(json.dumps(status, ensure_ascii=False))
            monitor.save_status()
            rounds += 1
            if max_rounds is not None and rounds >= max_rounds:
                break
            time.sleep(interval_sec)
    except KeyboardInterrupt:
        print("[monitor] 已停止")
    return monitor


# ---------------------------------------------------------------------------
# 可选：麦克风实时采集（需要 pyaudio）
# ---------------------------------------------------------------------------
def mic_capture_loop(seconds=10.0, sr=config.SAMPLE_RATE, chunk_sec=2.0):
    """从麦克风实时采集音频并检测（需安装 pyaudio，且本机有可用麦克风）。"""
    try:
        import pyaudio
    except ImportError:
        print("未安装 pyaudio，无法使用麦克风实时采集。"
              "请执行: pip install pyaudio （或使用文件夹监测模式）")
        return

    monitor = CoughMonitor()
    pa = pyaudio.PyAudio()
    stream = pa.open(format=pyaudio.paInt16, channels=1, rate=sr,
                     input=True, frames_per_buffer=int(sr * chunk_sec))
    print(f"[mic] 开始实时采集 {seconds} 秒 ...")
    start = time.time()
    buf = []
    try:
        while time.time() - start < seconds:
            data = stream.read(int(sr * chunk_sec))
            buf.append(np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0)
            seg = np.concatenate(buf)[-int(config.SEGMENT_SEC * sr):]
            p_cough = monitor.predict_waveform(seg, sr=sr)
            if p_cough >= config.CONFIDENCE_THRESHOLD:
                print(f"[mic] 检测到咳嗽 p={p_cough:.3f}")
    finally:
        stream.stop_stream(); stream.close(); pa.terminate()
