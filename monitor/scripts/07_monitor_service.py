# -*- coding: utf-8 -*-
"""
07_monitor_service.py —— 生产级猪咳嗽监测服务

功能：
  1) 文件夹轮询监测：采集端音频落盘到 watch_dir，本服务定时扫描处理并落库
  2) 单文件处理 / 批量回填：--once --file x.wav / --batch-dir dir
  3) 滑窗检测 + 事件合并（冷却时间去重）
  4) 结果写回 MySQL：cough_event / monitor_status / processed_audio / monitor_heartbeat
  5) 处理去重、心跳、断线重连、滚动日志、优雅退出、单实例锁

运行（在项目根目录下）：
  python monitor/scripts/07_monitor_service.py --init-db
  python monitor/scripts/07_monitor_service.py --watch-dir data/monitor_in --farm-code net01 --interval 10
  python monitor/scripts/07_monitor_service.py --once --file x.wav --farm-code net01
  python monitor/scripts/07_monitor_service.py --check
"""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # ?????????????

import argparse
import json
import logging
import os
import signal
import sys
import threading
import time
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pymysql

import config
from src.inference import load_model, predict_long_audio

# ===========================================================================
# 日志：控制台 + 滚动文件（10MB x 5）
# ===========================================================================
def build_logger(name="cough_monitor", log_dir=None, level=logging.INFO):
    log_dir = Path(log_dir or (getattr(config, "LOG_DIR", None) or (config.BASE_DIR / "logs")))
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(level)
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
# 监测结果数据库（结果落库）
# ===========================================================================
class MonitorDB:
    """监测结果 MySQL 封装：建表 / 写事件 / 写状态 / 去重 / 心跳 / 查询。"""

    def __init__(self, host=None, port=None, user=None, password=None,
                 db=None, charset=None, farm_code=None):
        self.params = dict(
            host=host or config.DB_HOST, port=port or config.DB_PORT,
            user=user or config.DB_USER, password=password or config.DB_PASSWORD,
            database=db or config.DB_NAME, charset=charset or config.DB_CHARSET,
            cursorclass=pymysql.cursors.DictCursor, connect_timeout=5,
        )
        self.farm_code = farm_code
        self.conn = None
        self._lock = threading.RLock()   # 多线程(心跳/监测/API)共用实例时串行访问连接

    # ---- 连接管理（带重连） ----
    def connect(self):
        if self.conn is None:
            self.conn = pymysql.connect(**self.params)
        return self.conn

    def _cursor(self):
        try:
            return self.connect().cursor()
        except pymysql.MySQLError:
            self.conn = None
            raise

    def _exec(self, sql, args=None, retries=3, backoff=1.0):
        """执行写操作，断线自动重连重试（线程安全）。"""
        with self._lock:
            last_err = None
            for i in range(retries):
                try:
                    cur = self._cursor()
                    cur.execute(sql, args)
                    self.conn.commit()
                    return cur
                except pymysql.MySQLError as e:
                    last_err = e
                    self.conn = None
                    time.sleep(backoff * (i + 1))
            raise last_err

    def ping(self):
        with self._lock:
            try:
                self._cursor().execute("SELECT 1")
                return True
            except Exception:
                return False

    # ---- 建表 ----
    def init_tables(self):
        ddl = [
            """
            CREATE TABLE IF NOT EXISTS `cough_event` (
              `id` BIGINT NOT NULL AUTO_INCREMENT,
              `farm_code` VARCHAR(32) NOT NULL,
              `device_id` VARCHAR(64) NULL,
              `audio_source` VARCHAR(512) NULL,
              `event_start` DATETIME NOT NULL,
              `event_end` DATETIME NOT NULL,
              `duration_sec` FLOAT NOT NULL,
              `confidence` FLOAT NOT NULL,
              `model_version` VARCHAR(64) NULL,
              `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY (`id`),
              KEY `idx_farm_time` (`farm_code`, `event_start`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
            """
            CREATE TABLE IF NOT EXISTS `monitor_status` (
              `id` BIGINT NOT NULL AUTO_INCREMENT,
              `farm_code` VARCHAR(32) NOT NULL,
              `status_time` DATETIME NOT NULL,
              `window_minutes` INT NOT NULL DEFAULT 60,
              `cough_count` INT NOT NULL DEFAULT 0,
              `baseline_hourly` FLOAT NULL,
              `alert_level` VARCHAR(16) NOT NULL DEFAULT 'normal',
              `alert_message` VARCHAR(500) NULL,
              `extra` JSON NULL,
              `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY (`id`),
              KEY `idx_farm_time` (`farm_code`, `status_time`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
            """
            CREATE TABLE IF NOT EXISTS `processed_audio` (
              `id` BIGINT NOT NULL AUTO_INCREMENT,
              `farm_code` VARCHAR(32) NOT NULL,
              `file_path` VARCHAR(512) NOT NULL,
              `file_mtime` DATETIME NULL,
              `processed_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY (`id`),
              UNIQUE KEY `uk_file_path` (`file_path`(255))
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
            """
            CREATE TABLE IF NOT EXISTS `monitor_heartbeat` (
              `id` BIGINT NOT NULL AUTO_INCREMENT,
              `farm_code` VARCHAR(32) NOT NULL,
              `host` VARCHAR(128) NULL,
              `pid` INT NULL,
              `started_at` DATETIME NULL,
              `last_beat` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              `status` VARCHAR(16) NOT NULL DEFAULT 'running',
              PRIMARY KEY (`id`),
              KEY `idx_farm` (`farm_code`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
        ]
        for sql in ddl:
            self._exec(sql)
        logger.info("数据库表结构已就绪（cough_event/monitor_status/processed_audio/monitor_heartbeat）")

    # ---- 写：咳嗽事件 ----
    def insert_cough_event(self, farm_code, device_id, audio_source,
                           event_start, event_end, confidence, model_version):
        self._exec(
            "INSERT INTO cough_event (farm_code, device_id, audio_source, event_start, "
            "event_end, duration_sec, confidence, model_version) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (farm_code, device_id, audio_source, event_start, event_end,
             (event_end - event_start).total_seconds(), float(confidence), model_version),
        )

    # ---- 写：监测状态 / 预警 ----
    def insert_monitor_status(self, farm_code, status_time, window_minutes,
                              cough_count, baseline, alert_level, alert_message, extra=None):
        self._exec(
            "INSERT INTO monitor_status (farm_code, status_time, window_minutes, "
            "cough_count, baseline_hourly, alert_level, alert_message, extra) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (farm_code, status_time, int(window_minutes), int(cough_count),
             float(baseline) if baseline is not None else None,
             alert_level, alert_message,
             json.dumps(extra, ensure_ascii=False) if extra else None),
        )

    # ---- 去重 ----
    def is_processed(self, file_path):
        cur = self._exec("SELECT 1 FROM processed_audio WHERE file_path=%s LIMIT 1",
                         (str(file_path),))
        return cur.fetchone() is not None

    def mark_processed(self, file_path, file_mtime=None):
        self._exec(
            "INSERT IGNORE INTO processed_audio (farm_code, file_path, file_mtime) "
            "VALUES (%s,%s,%s)",
            (self.farm_code or "unknown", str(file_path), file_mtime),
        )

    # ---- 心跳 ----
    def heartbeat(self, farm_code, host, pid, started_at, status="running"):
        self._exec(
            "INSERT INTO monitor_heartbeat (farm_code, host, pid, started_at, last_beat, status) "
            "VALUES (%s,%s,%s,%s,NOW(),%s) "
            "ON DUPLICATE KEY UPDATE last_beat=NOW(), status=VALUES(status)",
            (farm_code, host, pid, started_at, status),
        )

    # ---- 查询（供状态统计 / API 使用） ----
    def count_events(self, farm_code, since):
        cur = self._exec(
            "SELECT COUNT(*) AS n FROM cough_event WHERE farm_code=%s AND event_start>=%s",
            (farm_code, since))
        return int((cur.fetchone() or {"n": 0})["n"])

    def latest_status(self, farm_code):
        cur = self._exec(
            "SELECT * FROM monitor_status WHERE farm_code=%s ORDER BY status_time DESC, id DESC LIMIT 1",
            (farm_code,))
        return cur.fetchone()

    def query_events(self, farm_code=None, start=None, end=None,
                     page=1, page_size=50):
        where, args = [], []
        if farm_code:
            where.append("farm_code=%s"); args.append(farm_code)
        if start:
            where.append("event_start>=%s"); args.append(start)
        if end:
            where.append("event_start<=%s"); args.append(end)
        sql_where = ("WHERE " + " AND ".join(where)) if where else ""
        args_page = list(args) + [page_size, (page - 1) * page_size]
        cur = self._exec(
            "SELECT * FROM cough_event " + sql_where +
            " ORDER BY event_start DESC LIMIT %s OFFSET %s", args_page)
        return cur.fetchall()

    def query_alerts(self, farm_code=None, limit=20):
        where, args = ["alert_level<>'normal'"], []
        if farm_code:
            where.append("farm_code=%s"); args.append(farm_code)
        cur = self._exec(
            "SELECT * FROM monitor_status WHERE " + " AND ".join(where) +
            " ORDER BY status_time DESC LIMIT %s", args + [limit])
        return cur.fetchall()

    def close(self):
        with self._lock:
            if self.conn is not None:
                try:
                    self.conn.close()
                finally:
                    self.conn = None


# ===========================================================================
# 生产级监测引擎
# ===========================================================================
class MonitoringEngine:
    """监测引擎：处理音频 -> 落库事件 -> 周期统计 -> 预警 -> 心跳。"""

    def __init__(self, farm_code=None, device_id=None, model_path=None,
                 window_minutes=None, alert_per_hour=None, ratio_baseline=None,
                 model_version=None, db: MonitorDB = None):
        self.farm_code = farm_code or getattr(config, "MONITOR_FARM_CODE", "net01")
        self.device_id = device_id or getattr(config, "MONITOR_DEVICE_ID", None)
        self.window_minutes = window_minutes or getattr(config, "MONITOR_WINDOW_MINUTES", 60)
        self.alert_per_hour = alert_per_hour or config.ALERT_COUGH_PER_HOUR
        self.ratio_baseline = ratio_baseline or config.ALERT_RATIO_BASELINE
        self.model_version = model_version or getattr(config, "MONITOR_MODEL_VERSION", "cnn_bilstm_v1")
        self.db = db or MonitorDB(farm_code=self.farm_code)
        logger.info("加载模型 ...")
        self.model = load_model(model_path)
        logger.info("模型加载完成: %s", model_path or "默认模型")
        self._baseline = None            # 健康基线（指数滑动平均）
        self._stop = threading.Event()
        self._last_status_write = 0.0
        self._heartbeat_started_at = datetime.now()
        self._thread = None

    # ---------------- 对外控制 ----------------
    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._thread.start()
        return self

    def stop(self):
        self._stop.set()
        try:
            self.db.heartbeat(self.farm_code, _hostname(), os.getpid(),
                              self._heartbeat_started_at, status="stopped")
        except Exception:
            logger.exception("停止心跳失败")
        logger.info("监测服务收到停止信号")

    # ---------------- 核心：处理单个音频文件 ----------------
    def process_file(self, path):
        """处理一个音频：去重 -> 滑窗检测 -> 事件落库。返回事件列表。"""
        path = Path(path)
        key = str(path.resolve())
        if self.db.is_processed(key):
            logger.debug("已处理过，跳过: %s", key)
            return []
        try:
            res = predict_long_audio(self.model, str(path))
        except Exception as e:
            logger.warning("音频无法读取，标记为已处理并跳过（若已修复请删除 processed_audio 对应记录）: %s - %s", path, e)
            try:
                mtime = datetime.fromtimestamp(path.stat().st_mtime)
            except OSError:
                mtime = None
            self.db.mark_processed(key, mtime)
            return []
        events = []
        # 以文件修改时间作为音频起点，推算事件绝对时间
        try:
            audio_start = datetime.fromtimestamp(path.stat().st_mtime)
        except OSError:
            audio_start = datetime.now()
        for ev in res["events"]:
            start_dt = audio_start + timedelta(seconds=float(ev["start_sec"]))
            end_dt = audio_start + timedelta(seconds=float(ev["end_sec"]))
            self.db.insert_cough_event(
                farm_code=self.farm_code, device_id=self.device_id,
                audio_source=key,
                event_start=start_dt, event_end=end_dt,
                confidence=float(ev["confidence"]),
                model_version=self.model_version)
            events.append({
                "start": start_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                "end": end_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                "confidence": round(float(ev["confidence"]), 4),
            })
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime)
        except OSError:
            mtime = None
        self.db.mark_processed(key, mtime)
        return events

    # ---------------- 统计与预警 ----------------
    def evaluate(self, now=None):
        """统计窗口内咳嗽次数 + 更新基线 + 判断预警级别。"""
        now = now or datetime.now()
        since = now - timedelta(minutes=self.window_minutes)
        count = self.db.count_events(self.farm_code, since)
        if self._baseline is None:
            self._baseline = float(count)
        else:
            self._baseline = 0.8 * self._baseline + 0.2 * float(count)

        if count >= self.alert_per_hour:
            level = "critical" if count >= 2 * self.alert_per_hour else "warning"
            msg = f"近{self.window_minutes}分钟咳嗽 {count} 次，超过阈值 {self.alert_per_hour} 次/小时"
        elif self._baseline > 0 and count >= self.ratio_baseline * self._baseline:
            level = "warning"
            msg = f"近{self.window_minutes}分钟咳嗽 {count} 次，较基线 {self._baseline:.1f} 升高超过 {self.ratio_baseline:.0%}"
        else:
            level = "normal"
            msg = ""
        return {
            "farm_code": self.farm_code,
            "status_time": now.strftime("%Y-%m-%dT%H:%M:%S"),
            "window_minutes": self.window_minutes,
            "cough_count": count,
            "baseline_hourly": round(self._baseline, 2),
            "alert_level": level,
            "alert_message": msg,
        }

    def write_status(self, force=False):
        """周期性把状态写入 monitor_status（默认每 60s 一次，预警变化时立即写）。"""
        now = datetime.now()
        if not force and (time.time() - self._last_status_write) < \
                getattr(config, "MONITOR_WRITE_STATUS_EVERY_SEC", 60):
            return None
        status = self.evaluate(now)
        self.db.insert_monitor_status(
            farm_code=status["farm_code"], status_time=now,
            window_minutes=status["window_minutes"], cough_count=status["cough_count"],
            baseline=status["baseline_hourly"], alert_level=status["alert_level"],
            alert_message=status["alert_message"],
            extra={"model_version": self.model_version, "device_id": self.device_id})
        self._last_status_write = time.time()
        logger.info("状态写入: count=%d level=%s baseline=%.2f",
                    status["cough_count"], status["alert_level"], status["baseline_hourly"])
        return status

    # ---------------- 文件夹轮询监测 ----------------
    def run_folder_monitor(self, watch_dir, interval_sec=10.0,
                           exts=(".wav", ".mp3", ".flac", ".ogg"),
                           archive_dir=None, max_rounds=None):
        watch_dir = Path(watch_dir)
        watch_dir.mkdir(parents=True, exist_ok=True)
        logger.info("开始监测文件夹: %s (每 %ss 扫描一次)", watch_dir, interval_sec)
        rounds = 0
        while not self._stop.is_set() and (max_rounds is None or rounds < max_rounds):
            try:
                files = sorted(p for p in watch_dir.iterdir()
                               if p.is_file() and p.suffix.lower() in exts)
                for p in files:
                    if self._stop.is_set():
                        break
                    try:
                        events = self.process_file(p)
                        if events:
                            logger.info("%s: 检出 %d 个咳嗽事件", p.name, len(events))
                        if archive_dir:
                            Path(archive_dir).mkdir(parents=True, exist_ok=True)
                            p.replace(Path(archive_dir) / p.name)
                    except Exception:
                        logger.exception("处理文件失败: %s", p)
                # 周期写状态（预警变化时立即写）
                self.write_status()
            except Exception:
                logger.exception("监测循环异常")
            rounds += 1
            if max_rounds is not None and rounds >= max_rounds:
                break
            self._stop.wait(interval_sec)
        logger.info("监测结束，共扫描 %d 轮", rounds)

    def process_batch(self, batch_dir, exts=(".wav", ".mp3", ".flac", ".ogg")):
        """批量回填处理一个目录下的所有音频。"""
        batch_dir = Path(batch_dir)
        files = sorted(p for p in batch_dir.rglob("*")
                       if p.is_file() and p.suffix.lower() in exts)
        logger.info("批量回填 %d 个文件 ...", len(files))
        total = 0
        for p in files:
            try:
                evs = self.process_file(p)
                total += len(evs)
            except Exception:
                logger.exception("处理失败: %s", p)
        logger.info("批量回填完成，共入库 %d 个咳嗽事件", total)
        return total

    # ---------------- 心跳 ----------------
    def _heartbeat_loop(self):
        while not self._stop.wait(getattr(config, "MONITOR_HEARTBEAT_SEC", 30)):
            try:
                self.db.heartbeat(self.farm_code, _hostname(), os.getpid(),
                                  self._heartbeat_started_at, status="running")
            except Exception:
                logger.exception("心跳写入失败（将自动重试）")


def _hostname():
    try:
        import socket
        return socket.gethostname()
    except Exception:
        return "unknown"


# ===========================================================================
# 单实例锁（防止同一猪舍起两个监测进程重复入库）
# ===========================================================================
class SingleInstanceLock:
    def __init__(self, lock_path):
        self.lock_path = Path(lock_path)
        self.fd = None

    def acquire(self):
        try:
            self.lock_path.parent.mkdir(parents=True, exist_ok=True)
            self.fd = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(self.fd, str(os.getpid()).encode())
            return True
        except FileExistsError:
            logger.error("已有另一个监测实例在运行（锁文件 %s 存在），退出", self.lock_path)
            return False
        except OSError as e:
            logger.warning("无法创建单实例锁(%s)，继续运行: %s", self.lock_path, e)
            return True

    def release(self):
        if self.fd is not None:
            try:
                os.close(self.fd)
            finally:
                self.fd = None
        try:
            self.lock_path.unlink(missing_ok=True)
        except OSError:
            pass


# ===========================================================================
# 命令行入口
# ===========================================================================
def _parse_args(argv=None):
    p = argparse.ArgumentParser(description="生产级猪咳嗽监测服务")
    p.add_argument("--init-db", action="store_true", help="创建/校验监测结果表结构")
    p.add_argument("--check", action="store_true", help="自检：数据库/模型/目录")
    p.add_argument("--watch-dir", default=None, help="监测目录（采集端落盘目录）")
    p.add_argument("--archive-dir", default=None, help="处理完移入的目录（可选）")
    p.add_argument("--file", default=None, help="单文件处理（配合 --once）")
    p.add_argument("--batch-dir", default=None, help="批量回填目录")
    p.add_argument("--farm-code", default=None, help="猪场/栋舍编号")
    p.add_argument("--device-id", default=None, help="设备编号")
    p.add_argument("--interval", type=float, default=10.0, help="轮询间隔秒")
    p.add_argument("--rounds", type=int, default=None, help="轮询轮数（测试用）")
    p.add_argument("--once", action="store_true", help="处理一次后退出")
    p.add_argument("--no-lock", action="store_true", help="跳过单实例锁")
    return p.parse_args(argv)


def _self_check(engine):
    ok = True
    try:
        ok_db = engine.db.ping()
        print(f"[check] 数据库连接: {'OK' if ok_db else 'FAIL'}")
        ok = ok and ok_db
    except Exception as e:
        print(f"[check] 数据库连接: FAIL ({e})")
        ok = False
    try:
        _ = engine.model
        print("[check] 模型加载: OK")
    except Exception as e:
        print(f"[check] 模型加载: FAIL ({e})")
        ok = False
    return ok


def main(argv=None):
    args = _parse_args(argv)
    engine = MonitoringEngine(farm_code=args.farm_code, device_id=args.device_id)

    if args.init_db:
        engine.db.init_tables()
        print("表结构初始化完成，可开始监测。")
        return 0

    if args.check:
        return 0 if _self_check(engine) else 1

    lock = None
    if not args.no_lock:
        lock_path = getattr(config, "LOG_DIR", config.BASE_DIR / "logs") / f"monitor_{args.farm_code or 'default'}.lock"
        lock = SingleInstanceLock(lock_path)
        if not lock.acquire():
            return 1

    try:
        if args.file:
            if not Path(args.file).exists():
                logger.error("文件不存在: %s", args.file)
                return 1
            evs = engine.process_file(args.file)
            print(json.dumps(evs, ensure_ascii=False, indent=2))
            return 0
        if args.batch_dir:
            engine.process_batch(args.batch_dir)
            return 0

        watch_dir = args.watch_dir or getattr(config, "MONITOR_WATCH_DIR", "data/monitor_in")
        engine.start()
        # 优雅退出
        stop_event = threading.Event()
        def _on_signal(signum, frame):
            logger.info("收到信号 %s，正在退出 ...", signum)
            engine.stop()
            stop_event.set()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                signal.signal(sig, _on_signal)
            except (ValueError, OSError):
                pass
        engine.run_folder_monitor(watch_dir, interval_sec=args.interval,
                                  archive_dir=args.archive_dir, max_rounds=args.rounds)
        engine.stop()
    finally:
        if lock:
            lock.release()
        engine.db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())