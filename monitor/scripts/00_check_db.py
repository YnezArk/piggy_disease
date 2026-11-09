# -*- coding: utf-8 -*-
"""
00_check_db.py —— 检查数据库连接与本地文件映射（不改数据，只读）
    1) 连接 MySQL pig_cough_dataset
    2) 打印 audio_sample / dataset_stat 统计
    3) 校验每条样本能否在本地找到音频文件（按 audio_filename 与 relative_path）
运行：python scripts/00_check_db.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
from src.db import Database, scan_db_samples


def main():
    print("=" * 60)
    print(f"数据库: {config.DB_USER}@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}")
    print(f"本地音频根目录: {config.AUDIO_ROOT}")
    print("=" * 60)

    with Database() as db:
        rows = db.get_samples()
        stat = db.get_dataset_stat()
    print(f"audio_sample 共 {len(rows)} 条: "
          f"咳嗽(1) {sum(r['sample_type'] == 1 for r in rows)} / "
          f"非咳嗽(0) {sum(r['sample_type'] == 0 for r in rows)}")
    for s in stat:
        print(f"dataset_stat: date={s['stat_date']} pos={s['total_pos']} neg={s['total_neg']} "
              f"remark={s.get('remark')}")

    samples = scan_db_samples()
    found = [s for s in samples if s["exists"]]
    missing = [s for s in samples if not s["exists"]]
    print(f"\n本地文件匹配: 找到 {len(found)} / 缺失 {len(missing)}")
    if missing:
        print("缺失示例（前10个）:")
        for s in missing[:10]:
            print(f"  id={s['id']} {s['relative_path']}  <- 尝试过 audio_root/{s['cls_name']}/{s['audio_filename']}")
    if found:
        print("匹配示例（前5个）:")
        for s in found[:5]:
            print(f"  id={s['id']} [{s['cls_name']}] {s['path']}")

    # 分类统计
    from collections import Counter
    c = Counter((s["cls_name"]) for s in found)
    print("\n按类别: ", dict(c))


if __name__ == "__main__":
    main()