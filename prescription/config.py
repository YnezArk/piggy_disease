# config.py — 统一环境配置读取（项目根目录 .env）
# 所有 AI 模型/数据库连接参数集中于此，代码中禁止硬编码
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent          # prescription/
ROOT_DIR = BASE_DIR.parent                          # 项目根目录
load_dotenv(ROOT_DIR / ".env")

DATA_DIR = ROOT_DIR / "data"
KNOWLEDGE_DIR = DATA_DIR / "knowledge"
SQL_DIR = DATA_DIR / "sql"

# ── AI 模型（百炼自定义网关，OpenAI 兼容）──────────────
LLM_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
LLM_BASE_URL = os.environ.get(
    "DASHSCOPE_BASE_URL",
    "https://dashscope.aliyuncs.com/compatible-mode/v1",  # 官方网关兜底
)
LLM_MODEL = os.environ.get("DASHSCOPE_MODEL", "qwen-plus")

# 思考模式（Qwen3 系默认开启，会显著增加延迟）：
#   DASHSCOPE_ENABLE_THINKING=false 关闭；true 开启；未设置默认关闭
LLM_ENABLE_THINKING = os.environ.get("DASHSCOPE_ENABLE_THINKING", "false").lower() in (
    "1", "true", "yes", "on")

# ── 数据库（MySQL）────────────────────────────────────
DB = dict(
    host=os.environ.get("DB_HOST", "localhost"),
    port=int(os.environ.get("DB_PORT", "3306")),
    user=os.environ.get("DB_USER", "root"),
    password=os.environ.get("DB_PASS", ""),
    database=os.environ.get("DB_NAME", "pig_diag"),
    charset="utf8mb4",
)


def check_env():
    """环境配置自检：缺失项返回说明列表"""
    missing = []
    if not LLM_API_KEY:
        missing.append("DASHSCOPE_API_KEY（.env）")
    if not LLM_BASE_URL:
        missing.append("DASHSCOPE_BASE_URL（.env）")
    if not LLM_MODEL:
        missing.append("DASHSCOPE_MODEL（.env）")
    return missing
