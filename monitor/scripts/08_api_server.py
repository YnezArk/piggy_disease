# -*- coding: utf-8 -*-
"""
08_api_server.py —— 生产级 REST API（Flask）

接口：
  GET  /api/health                    健康检查（含 DB/模型状态）
  POST /api/predict                   上传单段音频 -> 咳嗽概率（可选落库 save_to_db=1）
  POST /api/predict_long              上传长音频 -> 咳嗽事件列表（可选落库 save_to_db=1）
  GET  /api/events                    查询咳嗽事件（分页，从数据库读）
  GET  /api/stats                     查询近 N 分钟统计 + 最近预警状态（从数据库读）
  GET  /api/alerts                    查询预警记录
  POST /api/monitor/start             后台启动文件夹监测
  POST /api/monitor/stop              停止后台监测
  GET  /api/monitor/status            查询监测进程状态

生产特性：
  - 可选 Token 鉴权（config.API_TOKEN 非空时启用，请求头 Authorization: Bearer <token>）
  - 请求日志 + 滚动文件日志
  - 上传大小限制(50MB) + 文件类型白名单
  - 模型线程安全懒加载（Flask 多线程下不会重复加载/竞争）
  - 监测结果全部从 MySQL 读取（多进程/云端共享状态）
  - 统一 JSON 错误返回
  - CORS（供 Web 前端联调；微信小程序不需要）

部署：
  本地调试:  python scripts\08_api_server.py --debug
  Windows:   pip install waitress
             waitress-serve --listen=0.0.0.0:5000 --threads=8 scripts.wsgi:app
  Linux:     pip install gunicorn
             gunicorn -w 2 -b 0.0.0.0:5000 "scripts.wsgi:app"
"""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # ?????????????

import argparse
import logging
import os
import sys
import threading
import time
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path

from flask import Flask, jsonify, request

import config


# ===========================================================================
# 日志
# ===========================================================================
def build_logger(name="cough_api", log_dir=None):
    log_dir = Path(log_dir or (getattr(config, "LOG_DIR", None) or (config.BASE_DIR / "logs")))
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    fh = RotatingFileHandler(log_dir / f"{name}.log", maxBytes=10 * 1024 * 1024,
                             backupCount=5, encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


logger = build_logger()

# ===========================================================================
# 模型：线程安全懒加载
# ===========================================================================
_model = None
_model_lock = threading.Lock()


def get_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from src.inference import load_model
                _model = load_model()
                logger.info("模型加载完成")
    return _model


# ===========================================================================
# 数据库（读结果 + 可选落库）
# ===========================================================================
def get_monitor_db():
    """monitor_service.MonitorDB 实例（每进程一个）。"""
    global _db
    if _db is None:
        import importlib
        mon = importlib.import_module("07_monitor_service")
        _db = mon.MonitorDB()
    return _db


_db = None

# ===========================================================================
# 监测引擎（后台线程，供 /api/monitor/* 控制）
# ===========================================================================
_engine = None
_engine_lock = threading.Lock()


def get_engine(farm_code=None):
    global _engine
    with _engine_lock:
        if _engine is None:
            import importlib
            mon = importlib.import_module("07_monitor_service")
            _engine = mon.MonitoringEngine(farm_code=farm_code, db=get_monitor_db())
            _engine.start()
    return _engine


# ===========================================================================
# Flask App
# ===========================================================================
ALLOWED_EXTS = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}
UPLOAD_DIR = Path(getattr(config, "UPLOAD_DIR", None) or (config.BASE_DIR / "data" / "uploads"))


def create_app():
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024   # 50MB
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # ---------- 通用：Token 鉴权 + CORS + 请求日志 ----------
    @app.before_request
    def _auth():
        token = getattr(config, "API_TOKEN", "") or ""
        if not token:
            return None
        if request.path == "/api/health":
            return None
        auth = request.headers.get("Authorization", "")
        given = auth[7:] if auth.startswith("Bearer ") else request.args.get("token", "")
        if given != token:
            return jsonify({"error": "未授权或 Token 错误"}), 401
        return None

    @app.after_request
    def _after(resp):
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        if request.method == "OPTIONS":
            return resp
        logger.info("%s %s -> %s", request.method, request.path, resp.status_code)
        return resp

    # ---------- 健康检查 ----------
    @app.route("/api/health", methods=["GET"])
    def health():
        db_ok = False
        try:
            db_ok = get_monitor_db().ping()
        except Exception as e:
            logger.warning("health: db ping failed: %s", e)
        model_ok = False
        try:
            get_model()
            model_ok = True
        except Exception as e:
            logger.warning("health: model load failed: %s", e)
        return jsonify({
            "status": "ok" if (db_ok and model_ok) else "degraded",
            "db": db_ok, "model": model_ok,
            "time": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        })

    # ---------- 工具 ----------
    def _save_upload(f):
        suffix = Path(f.filename or "").suffix.lower()
        if suffix not in ALLOWED_EXTS:
            raise ValueError(f"不支持的文件类型: {suffix or '未知'}")
        tmp = UPLOAD_DIR / f"upload_{int(time.time()*1000)}_{os.getpid()}{suffix}"
        f.save(str(tmp))
        return tmp

    def _cleanup(path):
        try:
            Path(path).unlink(missing_ok=True)
        except OSError:
            pass

    # ---------- 识别接口 ----------
    @app.route("/api/predict", methods=["POST"])
    def predict():
        f = request.files.get("file")
        if f is None:
            return jsonify({"error": "缺少 file 字段"}), 400
        path = None
        try:
            path = _save_upload(f)
            from src.inference import predict_audio_file
            p_cough, p_non = predict_audio_file(get_model(), str(path))
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            logger.exception("predict 失败")
            return jsonify({"error": f"识别失败: {e}"}), 500
        finally:
            if path is not None:
                _cleanup(path)

        label = "cough" if p_cough >= config.CONFIDENCE_THRESHOLD else "non_cough"
        resp = {"prob_cough": round(p_cough, 4), "prob_non_cough": round(p_non, 4), "label": label}

        # 可选落库：save_to_db=1
        if request.form.get("save_to_db") == "1":
            try:
                farm = request.form.get("farm_code") or getattr(config, "MONITOR_FARM_CODE", "net01")
                now = datetime.now()
                get_monitor_db().insert_cough_event(
                    farm_code=farm, device_id=request.form.get("device_id"),
                    audio_source="api_predict",
                    event_start=now - timedelta(seconds=config.SEGMENT_SEC),
                    event_end=now, confidence=p_cough,
                    model_version=getattr(config, "MONITOR_MODEL_VERSION", "cnn_bilstm_v1"))
                resp["saved"] = True
            except Exception as e:
                logger.exception("落库失败")
                resp["saved"] = False
                resp["save_error"] = str(e)
        return jsonify(resp)

    @app.route("/api/predict_long", methods=["POST"])
    def predict_long():
        f = request.files.get("file")
        if f is None:
            return jsonify({"error": "缺少 file 字段"}), 400
        path = None
        try:
            path = _save_upload(f)
            from src.inference import predict_long_audio
            result = predict_long_audio(get_model(), str(path))
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            logger.exception("predict_long 失败")
            return jsonify({"error": f"识别失败: {e}"}), 500
        finally:
            if path is not None:
                _cleanup(path)

        if request.form.get("save_to_db") == "1":
            saved = 0
            try:
                farm = request.form.get("farm_code") or getattr(config, "MONITOR_FARM_CODE", "net01")
                db = get_monitor_db()
                audio_start = datetime.now() - timedelta(seconds=result["duration_sec"])
                for ev in result["events"]:
                    db.insert_cough_event(
                        farm_code=farm, device_id=request.form.get("device_id"),
                        audio_source="api_predict_long",
                        event_start=audio_start + timedelta(seconds=ev["start_sec"]),
                        event_end=audio_start + timedelta(seconds=ev["end_sec"]),
                        confidence=ev["confidence"],
                        model_version=getattr(config, "MONITOR_MODEL_VERSION", "cnn_bilstm_v1"))
                    saved += 1
                result["saved"] = saved
            except Exception as e:
                logger.exception("落库失败")
                result["saved"] = 0
                result["save_error"] = str(e)
        return jsonify(result)

    # ---------- 查询接口（从数据库读，云端共享） ----------
    @app.route("/api/events", methods=["GET"])
    def events():
        try:
            db = get_monitor_db()
            farm = request.args.get("farm_code")
            start = request.args.get("start")       # 2026-08-17T00:00:00
            end = request.args.get("end")
            page = max(1, int(request.args.get("page", 1)))
            page_size = min(200, max(1, int(request.args.get("page_size", 50))))
            rows = db.query_events(farm_code=farm, start=start, end=end,
                                   page=page, page_size=page_size)
            return jsonify({"farm_code": farm, "page": page, "page_size": page_size,
                            "count": len(rows), "events": rows})
        except Exception as e:
            logger.exception("查询事件失败")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/stats", methods=["GET"])
    def stats():
        try:
            db = get_monitor_db()
            farm = request.args.get("farm_code") or getattr(config, "MONITOR_FARM_CODE", "net01")
            minutes = int(request.args.get("minutes", 60))
            since = datetime.now() - timedelta(minutes=minutes)
            count = db.count_events(farm, since)
            latest = db.latest_status(farm) or {}
            return jsonify({
                "farm_code": farm,
                "window_minutes": minutes,
                "cough_count": count,
                "baseline_hourly": latest.get("baseline_hourly"),
                "alert_level": latest.get("alert_level", "normal"),
                "alert_message": latest.get("alert_message"),
                "last_status_time": latest.get("status_time"),
                "time": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            })
        except Exception as e:
            logger.exception("查询统计失败")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/alerts", methods=["GET"])
    def alerts():
        try:
            db = get_monitor_db()
            farm = request.args.get("farm_code")
            limit = min(100, int(request.args.get("limit", 20)))
            rows = db.query_alerts(farm_code=farm, limit=limit)
            return jsonify({"count": len(rows), "alerts": rows})
        except Exception as e:
            logger.exception("查询预警失败")
            return jsonify({"error": str(e)}), 500

    # ---------- 监测控制（后台引擎） ----------
    @app.route("/api/monitor/start", methods=["POST"])
    def monitor_start():
        try:
            body = request.get_json(silent=True) or {}
            farm = body.get("farm_code") or getattr(config, "MONITOR_FARM_CODE", "net01")
            watch_dir = body.get("watch_dir") or getattr(config, "MONITOR_WATCH_DIR", "data/monitor_in")
            interval = float(body.get("interval", 10))
            archive_dir = body.get("archive_dir")
            engine = get_engine(farm_code=farm)
            t = threading.Thread(target=engine.run_folder_monitor,
                                 args=(watch_dir, interval),
                                 kwargs={"archive_dir": archive_dir},
                                 daemon=True)
            t.start()
            logger.info("后台监测已启动: dir=%s farm=%s interval=%ss", watch_dir, farm, interval)
            return jsonify({"status": "started", "farm_code": farm, "watch_dir": watch_dir})
        except Exception as e:
            logger.exception("启动监测失败")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/monitor/stop", methods=["POST"])
    def monitor_stop():
        try:
            with _engine_lock:
                if _engine is not None:
                    _engine.stop()
                    return jsonify({"status": "stopping"})
            return jsonify({"status": "not_running"}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/monitor/status", methods=["GET"])
    def monitor_status():
        try:
            farm = request.args.get("farm_code") or getattr(config, "MONITOR_FARM_CODE", "net01")
            latest = get_monitor_db().latest_status(farm) or {}
            return jsonify({"farm_code": farm, "latest_status": latest,
                            "engine_alive": _engine is not None})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return app


app = create_app()


# ===========================================================================
# 启动入口
# ===========================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=os.getenv("API_HOST", "0.0.0.0"))
    ap.add_argument("--port", type=int, default=int(os.getenv("API_PORT", "5000")))
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()
    logger.info("启动 API: http://%s:%s (debug=%s)", args.host, args.port, args.debug)
    # 生产环境优先用 waitress（跨平台、稳定、支持 Windows）
    try:
        from waitress import serve
        serve(app, host=args.host, port=args.port, threads=8)
    except ImportError:
        app.run(host=args.host, port=args.port, debug=args.debug, threaded=True)


if __name__ == "__main__":
    main()

