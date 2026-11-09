# -*- coding: utf-8 -*-
"""
11_export_db_sql.py —— 导出数据库部署 SQL
从当前训练集 data/raw/monitor/{cough,non_cough} 生成 data/sql/pig_cough_dataset.sql：
  - 建库建表 audio_sample（301 个当前训练样本，含真实元数据）
  - dataset_stat 统计
  - 4 张监测结果表（cough_event / monitor_status / processed_audio / monitor_heartbeat）
运行：python scripts\11_export_db_sql.py
"""
import sys
import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import soundfile as sf

import config

OUT = config.SQL_DIR / "pig_cough_dataset.sql"
FARM = "net01"


def main():
    # ---- 扫描训练集 ----
    rows = []
    for cls_name, st in (("cough", 1), ("non_cough", 0)):
        d = config.RAW_DIR / cls_name
        if not d.exists():
            print(f"[warn] 目录不存在: {d}")
            continue
        for p in sorted(d.glob("*.wav")):
            try:
                info = sf.info(str(p))
                mtime = datetime.datetime.fromtimestamp(p.stat().st_mtime)
                rows.append({
                    "farm": FARM,
                    "pig": f"{FARM}{len(rows)+1:05d}",
                    "st": st,
                    "filename": p.name,
                    "rel": f"{cls_name}/{p.name}",
                    "dur": round(float(info.duration), 2),
                    "sr": int(info.samplerate),
                    "size": int(p.stat().st_size),
                    "time": mtime.strftime("%Y-%m-%d %H:%M:%S"),
                })
            except Exception as e:
                print(f"[warn] 读取失败 {p}: {e}")

    n_pos = sum(1 for r in rows if r["st"] == 1)
    n_neg = sum(1 for r in rows if r["st"] == 0)

    L = []
    A = L.append
    A("-- ============================================================")
    A("-- 猪咳嗽声智能监测系统 数据库部署脚本")
    A("-- 生成时间: %s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    A("-- 训练集来源: data/raw/{cough,non_cough} (共 %d 个, 咳嗽 %d / 非咳嗽 %d)" % (len(rows), n_pos, n_neg))
    A("-- ============================================================")
    A("SET NAMES utf8mb4;")
    A("SET FOREIGN_KEY_CHECKS = 0;")
    A("")
    A("CREATE DATABASE IF NOT EXISTS `pig_cough_dataset` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    A("USE `pig_cough_dataset`;")
    A("")
    A("-- ----------------------------")
    A("-- Table structure for audio_sample")
    A("-- ----------------------------")
    A("DROP TABLE IF EXISTS `audio_sample`;")
    A("""CREATE TABLE `audio_sample` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '样本唯一ID',
  `farm_code` varchar(32) NOT NULL COMMENT '猪场编号',
  `pig_id` varchar(32) NOT NULL COMMENT '猪只编号',
  `sample_type` tinyint NOT NULL COMMENT '1=咳嗽正样本，0=无咳嗽负样本',
  `audio_filename` varchar(128) NOT NULL COMMENT '音频文件名',
  `relative_path` varchar(256) NOT NULL COMMENT '音频相对路径',
  `audio_duration` float NOT NULL COMMENT '音频时长秒',
  `sample_rate` int NOT NULL COMMENT '采样率',
  `file_size` int NOT NULL COMMENT '文件大小字节',
  `record_time` datetime NOT NULL COMMENT '录制时间',
  `annotator` varchar(32) DEFAULT NULL COMMENT '标注人',
  `dataset_split` tinyint NOT NULL DEFAULT 0 COMMENT '0未划分 1训练集 2验证集 3测试集',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_sample_type` (`sample_type`),
  KEY `idx_dataset_split` (`dataset_split`),
  KEY `idx_farm` (`farm_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='生猪咳嗽音频样本总表';""")
    A("")
    A("-- ----------------------------")
    A("-- Records of audio_sample")
    A("-- ----------------------------")
    for r in rows:
        A("INSERT INTO `audio_sample` (farm_code, pig_id, sample_type, audio_filename, relative_path, "
          "audio_duration, sample_rate, file_size, record_time, annotator, dataset_split) VALUES "
          "('%s', '%s', %d, '%s', '%s', %.2f, %d, %d, '%s', '%s', 0);"
          % (r["farm"], r["pig"], r["st"], r["filename"], r["rel"],
             r["dur"], r["sr"], r["size"], r["time"], ""))
    A("")
    A("-- ----------------------------")
    A("-- Table structure for dataset_stat")
    A("-- ----------------------------")
    A("DROP TABLE IF EXISTS `dataset_stat`;")
    A("""CREATE TABLE `dataset_stat` (
  `stat_id` int NOT NULL AUTO_INCREMENT,
  `stat_date` date NOT NULL,
  `total_pos` int NOT NULL,
  `total_neg` int NOT NULL,
  `train_pos` int DEFAULT NULL,
  `train_neg` int DEFAULT NULL,
  `val_pos` int DEFAULT NULL,
  `val_neg` int DEFAULT NULL,
  `test_pos` int DEFAULT NULL,
  `test_neg` int DEFAULT NULL,
  `remark` varchar(500) DEFAULT NULL,
  PRIMARY KEY (`stat_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='数据集均衡统计记录表';""")
    A("INSERT INTO `dataset_stat` (stat_date, total_pos, total_neg, train_pos, train_neg, val_pos, val_neg, test_pos, test_neg, remark) "
      "VALUES ('%s', %d, %d, 0, 0, 0, 0, 0, 0, '训练集由 scripts/10_build_retrain_dataset.py 整理');"
      % (datetime.date.today().isoformat(), n_pos, n_neg))
    A("")
    A("-- ----------------------------")
    A("-- Monitoring tables (监测结果落库)")
    A("-- ----------------------------")
    A("""CREATE TABLE IF NOT EXISTS `cough_event` (
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='咳嗽事件记录';""")
    A("""CREATE TABLE IF NOT EXISTS `monitor_status` (
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='监测状态与预警记录';""")
    A("""CREATE TABLE IF NOT EXISTS `processed_audio` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `farm_code` VARCHAR(32) NOT NULL,
  `file_path` VARCHAR(512) NOT NULL,
  `file_mtime` DATETIME NULL,
  `processed_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_file_path` (`file_path`(255))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='已处理音频去重表';""")
    A("""CREATE TABLE IF NOT EXISTS `monitor_heartbeat` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `farm_code` VARCHAR(32) NOT NULL,
  `host` VARCHAR(128) NULL,
  `pid` INT NULL,
  `started_at` DATETIME NULL,
  `last_beat` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `status` VARCHAR(16) NOT NULL DEFAULT 'running',
  PRIMARY KEY (`id`),
  KEY `idx_farm` (`farm_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='监测进程心跳表';""")
    A("")
    A("SET FOREIGN_KEY_CHECKS = 1;")
    A("")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"SQL 已生成: {OUT}")
    print(f"样本: 共 {len(rows)} (咳嗽 {n_pos} / 非咳嗽 {n_neg})")


if __name__ == "__main__":
    main()