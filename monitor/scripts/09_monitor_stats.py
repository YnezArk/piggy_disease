# -*- coding: utf-8 -*-
"""
09_monitor_stats.py —— 查看监测结果（从数据库读）
    python scripts\09_monitor_stats.py [--farm net01] [--hours 24]
输出：近N小时咳嗽事件数、最近事件、最新状态、最近预警。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
from datetime import datetime, timedelta

import pymysql

import config


def main(args):
    conn = pymysql.connect(host=config.DB_HOST, port=config.DB_PORT,
                           user=config.DB_USER, password=config.DB_PASSWORD,
                           database=config.DB_NAME, charset=config.DB_CHARSET,
                           cursorclass=pymysql.cursors.DictCursor)
    cur = conn.cursor()
    farm = args.farm
    since = datetime.now() - timedelta(hours=args.hours)

    cur.execute("SELECT COUNT(*) n FROM cough_event WHERE farm_code=%s AND event_start>=%s", (farm, since))
    recent = cur.fetchone()["n"]
    cur.execute("SELECT COUNT(*) n FROM cough_event WHERE farm_code=%s", (farm,))
    total = cur.fetchone()["n"]
    print(f"[{farm}] 近{args.hours}小时咳嗽事件: {recent} | 累计: {total}")

    cur.execute("SELECT * FROM cough_event WHERE farm_code=%s ORDER BY event_start DESC LIMIT 10", (farm,))
    rows = cur.fetchall()
    print("最近事件:")
    for r in rows:
        print(f"  {r['event_start']} ~ {r['event_end']}  conf={r['confidence']:.3f}  src={r['audio_source']}")

    cur.execute("SELECT * FROM monitor_status WHERE farm_code=%s ORDER BY status_time DESC, id DESC LIMIT 1", (farm,))
    st = cur.fetchone()
    if st:
        print(f"最新状态: time={st['status_time']} count={st['cough_count']} "
              f"baseline={st['baseline_hourly']} level={st['alert_level']} msg={st['alert_message']}")
    else:
        print("暂无 monitor_status 记录（未运行过状态落库）")

    cur.execute("SELECT * FROM monitor_status WHERE farm_code=%s AND alert_level<>'normal' ORDER BY status_time DESC LIMIT 5", (farm,))
    alerts = cur.fetchall()
    print(f"最近预警: {len(alerts)} 条")
    for a in alerts:
        print(f"  {a['status_time']} {a['alert_level']} {a['alert_message']}")
    conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--farm", default=config.MONITOR_FARM_CODE)
    ap.add_argument("--hours", type=int, default=24)
    main(ap.parse_args())