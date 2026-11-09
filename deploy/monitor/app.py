# -*- coding: utf-8 -*-
"""
猪咳嗽声智能监测 —— HTTP 服务
  POST /api/monitor   请求 {audioUrl, shedInfo, temperature, mentalState}
                      返回 {code, message, data:{status, coughRate, confidence, details:{coughCount, averageInterval}}}
  GET  /health        健康检查
  GET  /static/<file> 测试辅助（可放测试音频用于 /api/monitor 的 audioUrl 测试）
"""
from __future__ import annotations

import logging
import os
import subprocess
import threading
import uuid
from datetime import datetime
from pathlib import Path

import requests
from flask import Flask, jsonify, request, send_from_directory

import config
from src.inference import load_model, predict_long_audio

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("cough_http")

# ---------------- 模型（懒加载 + 线程锁） ----------------
_model = None
_model_lock = threading.Lock()


def get_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                _model = load_model()
                logger.info("模型加载完成")
    return _model


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024

BASE_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = Path(os.environ.get("DOWNLOAD_DIR", str(BASE_DIR / "downloads")))
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_SUFFIX = (".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac")

# 状态分级阈值：每分钟咳嗽次数（可环境变量覆盖）
RATE_WARNING = float(os.environ.get("RATE_WARNING", 5))
RATE_DANGER = float(os.environ.get("RATE_DANGER", 15))


def _download_audio(url):
    """下载 audioUrl 到本地临时文件，返回路径。"""
    r = requests.get(url, timeout=60, stream=True)
    r.raise_for_status()
    suffix = Path(url.split("?")[0]).suffix.lower()
    if suffix not in ALLOWED_SUFFIX:
        suffix = ".wav"
    path = DOWNLOAD_DIR / f"{uuid.uuid4().hex}{suffix}"
    with open(path, "wb") as f:
        for chunk in r.iter_content(chunk_size=65536):
            if chunk:
                f.write(chunk)
    return path


def _to_readable_audio(path):
    """确保文件可被 soundfile 读取；不行则用 ffmpeg 转成 wav。"""
    import soundfile as sf
    try:
        sf.info(str(path))
        return path
    except Exception:
        logger.warning("soundfile 无法读取 %s，尝试 ffmpeg 转换", path)
        out = path.with_suffix(".wav")
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(path), "-ar", "44100", "-ac", "1", str(out)],
            check=True, capture_output=True)
        return out


def _compute_status(cough_rate):
    if cough_rate >= RATE_DANGER:
        return "danger"
    if cough_rate >= RATE_WARNING:
        return "warning"
    return "normal"


# ---------------- 接口 ----------------
@app.route("/health", methods=["GET"])
def health():
    try:
        get_model()
        model_ok = True
    except Exception as e:
        logger.exception("health: model load failed")
        model_ok = False
    return jsonify({
        "status": "ok" if model_ok else "model_load_failed",
        "service": "pig-cough-monitor",
        "version": getattr(config, "MONITOR_MODEL_VERSION", "cnn_bilstm_v1"),
        "time": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    })


@app.route("/static/<path:filename>", methods=["GET"])
def static_file(filename):
    return send_from_directory(str(STATIC_DIR), filename)


@app.route("/api/monitor", methods=["POST"])
def api_monitor():
    data = request.get_json(silent=True) or {}
    audio_url = data.get("audioUrl")
    if not audio_url:
        return jsonify({"code": 400, "message": "缺少 audioUrl", "data": None}), 400

    tmp = None
    try:
        tmp = _download_audio(audio_url)
        tmp = _to_readable_audio(tmp)
        result = predict_long_audio(get_model(), str(tmp))
    except Exception as e:
        logger.exception("处理失败: audioUrl=%s", audio_url)
        return jsonify({"code": 500, "message": f"音频处理失败: {e}", "data": None}), 200
    finally:
        if tmp and Path(tmp).exists():
            try:
                Path(tmp).unlink()
            except OSError:
                pass

    duration = max(float(result["duration_sec"]), 1e-6)
    cough_count = int(result["cough_count"])
    events = result["events"]
    cough_rate = round(cough_count / (duration / 60.0), 2)          # 次/分钟
    confidence = round(max((e["confidence"] for e in events), default=0.0), 4)
    average_interval = round(duration / cough_count, 2) if cough_count > 0 else 0.0
    status = _compute_status(cough_rate)

    logger.info("audioUrl=%s 时长=%.1fs 咳嗽=%d 频次=%.1f/min 状态=%s",
                audio_url, duration, cough_count, cough_rate, status)

    return jsonify({
        "code": 200,
        "message": "success",
        "data": {
            "status": status,
            "coughRate": cough_rate,
            "confidence": confidence,
            "details": {"coughCount": cough_count, "averageInterval": average_interval},
        },
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), debug=False)