# -*- coding: utf-8 -*-
"""
数据库访问层（MySQL：pig_cough_dataset）
  - audio_sample：音频样本元数据表
      sample_type   : 1=咳嗽正样本 / 0=非咳嗽负样本
      audio_filename: 音频文件名（如 1.wav）
      relative_path : 音频相对路径（如 cough/farm_net01/1.wav）
      dataset_split : 0未划分 / 1训练集 / 2验证集 / 3测试集
  - dataset_stat   : 数据集均衡统计表
本模块只负责"读样本清单 + 可选写回划分"，音频本体仍在本地磁盘。
"""
from __future__ import annotations

from pathlib import Path

import pymysql

import config


class Database:
    """MySQL 连接封装（PyMySQL）。"""

    def __init__(self, host=None, port=None, user=None, password=None,
                 db=None, charset=None):
        self.host = host or config.DB_HOST
        self.port = port or config.DB_PORT
        self.user = user or config.DB_USER
        self.password = password if password is not None else config.DB_PASSWORD
        self.db = db or config.DB_NAME
        self.charset = charset or config.DB_CHARSET
        self.conn = None

    def connect(self):
        self.conn = pymysql.connect(
            host=self.host, port=self.port, user=self.user,
            password=self.password, database=self.db, charset=self.charset,
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=5,
        )
        return self.conn

    def _cursor(self):
        if self.conn is None:
            self.connect()
        return self.conn.cursor()

    def get_samples(self, split=None):
        """读取 audio_sample 全部样本（或指定 dataset_split 的样本）。

        Returns
        -------
        list[dict] : 每行含 id/farm_code/pig_id/sample_type/audio_filename/
                     relative_path/audio_duration/sample_rate/record_time/dataset_split
        """
        cur = self._cursor()
        if split is None:
            sql = "SELECT * FROM audio_sample ORDER BY id"
            cur.execute(sql)
        else:
            sql = "SELECT * FROM audio_sample WHERE dataset_split = %s ORDER BY id"
            cur.execute(sql, (split,))
        return cur.fetchall()

    def get_dataset_stat(self):
        """读取 dataset_stat 统计表。"""
        cur = self._cursor()
        cur.execute("SELECT * FROM dataset_stat ORDER BY stat_id")
        return cur.fetchall()

    def update_dataset_split(self, id_to_split):
        """把 {sample_id: split(1/2/3)} 写回 audio_sample.dataset_split。

        Returns
        -------
        int : 更新的行数
        """
        cur = self._cursor()
        n = 0
        for sid, sp in id_to_split.items():
            cur.execute("UPDATE audio_sample SET dataset_split=%s WHERE id=%s", (int(sp), int(sid)))
            n += cur.rowcount
        self.conn.commit()
        return n

    def close(self):
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *exc):
        self.close()


# ---------------------------------------------------------------------------
# 路径解析：把数据库记录映射到本地真实音频文件
# ---------------------------------------------------------------------------
def resolve_audio_path(row, audio_root=None):
    """按优先级尝试解析本地音频路径：
      1) audio_root / <本地类别目录> / audio_filename   （你本地扁平结构 data/raw/cough/1.wav）
      2) audio_root / relative_path                    （同学交付结构 cough/farm_net01/1.wav）
      3) 顶层目录按 DB_PATH_MAP 替换后的 relative_path
    返回第一个存在的路径；都不存在返回 None。
    """
    audio_root = Path(audio_root or config.AUDIO_ROOT)
    filename = str(row.get("audio_filename") or "")
    rel = str(row.get("relative_path") or "")
    sample_type = int(row.get("sample_type"))
    top_local = "cough" if sample_type == 1 else "non_cough"

    candidates = []
    if filename:
        candidates.append(audio_root / top_local / filename)
    if rel:
        rel_path = Path(rel)
        candidates.append(audio_root / rel_path)
        parts = list(rel_path.parts)
        if parts:
            mapped = config.DB_PATH_MAP.get(parts[0], parts[0])
            parts[0] = mapped
            candidates.append(audio_root / Path(*parts))
    for c in candidates:
        if c.exists():
            return c
    return None


def scan_db_samples(split=None, audio_root=None, only_existing=False):
    """从数据库读取样本清单并解析本地路径。

    Returns
    -------
    list[dict] : {id, sample_type, label, cls_name, audio_filename,
                  relative_path, split, path(Path|None), exists}
      label: 0=咳嗽, 1=非咳嗽（对应 config.CLASS_NAMES）
    """
    with Database() as db:
        rows = db.get_samples(split=split)
    out = []
    for r in rows:
        path = resolve_audio_path(r, audio_root=audio_root)
        st = int(r["sample_type"])
        label = 0 if st == 1 else 1
        out.append({
            "id": int(r["id"]),
            "sample_type": st,
            "label": label,
            "cls_name": config.CLASS_NAMES[label],
            "audio_filename": r.get("audio_filename"),
            "relative_path": r.get("relative_path"),
            "split": int(r.get("dataset_split") or 0),
            "path": path,
            "exists": path is not None,
        })
    if only_existing:
        out = [x for x in out if x["exists"]]
    return out