# -*- coding: utf-8 -*-
"""
12_reset_monitor.py —— 重置监测结果（清空去重表/事件表）
用途：换新模型后想对旧音频全量重跑时使用；正常增量监测不需要。

    python scripts\12_reset_monitor.py            # 只清 processed_audio（去重表）
    python scripts\12_reset_monitor.py --events   # 同时清 cough_event / monitor_status
    python scripts\12_reset_monitor.py --all      # 清空全部 4 张监测表
"""
import sys
import argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pymysql

import config


def main(args):
    conn = pymysql.connect(host=config.DB_HOST, port=config.DB_PORT,
                           user=config.DB_USER, password=config.DB_PASSWORD,
                           database=config.DB_NAME, charset=config.DB_CHARSET)
    cur = conn.cursor()
    tables = ["processed_audio"]
    if args.events or args.all:
        tables += ["cough_event", "monitor_status"]
    if args.all:
        tables.append("monitor_heartbeat")
    for t in tables:
        cur.execute("DELETE FROM `%s`" % t)
        print("已清空:", t)
    conn.commit()
    conn.close()
    print("完成。之后重新运行 run_full_pipeline.bat（或 batch-dir）即会对全部音频用当前模型重跑。")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="重置监测结果表")
    ap.add_argument("--events", action="store_true", help="同时清空 cough_event / monitor_status")
    ap.add_argument("--all", action="store_true", help="清空全部监测表")
    main(ap.parse_args())