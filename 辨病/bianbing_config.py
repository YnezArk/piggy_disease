# -*- coding: utf-8 -*-
"""
辨病模块 — 统一环境配置（读取项目根目录 .env，禁止硬编码）

用法：
  from config import DB_CONFIG

所有 DB 连接参数从根目录 .env 读取（DB_HOST/DB_PORT/DB_USER/DB_PASS/DB_NAME），
缺失时回退默认值（仅 localhost/root 等无敏感信息项，密码无默认值）。
"""
import os
from dotenv import load_dotenv

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 项目根目录
load_dotenv(os.path.join(ROOT_DIR, ".env"))

DB_CONFIG = dict(
    host=os.environ.get("DB_HOST", "localhost"),
    port=int(os.environ.get("DB_PORT", "3306")),
    user=os.environ.get("DB_USER", "root"),
    password=os.environ.get("DB_PASS", ""),
    database=os.environ.get("DB_NAME", "pig_diag_v2"),
    charset="utf8mb4",
)

# 特征/数据路径（可在 .env 覆盖）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_ROOT = os.environ.get("BIANBING_AUDIO_ROOT", os.path.join(BASE_DIR, "pig_cough_data"))
FEAT_DIR = os.environ.get("BIANBING_FEAT_DIR", os.path.join(BASE_DIR, "features"))
MODEL_DIR = os.environ.get("BIANBING_MODEL_DIR", os.path.join(BASE_DIR, "models"))
