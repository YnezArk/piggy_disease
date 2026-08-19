# config.py — release 统一环境配置（读取本目录 .env，禁止硬编码）
import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# ── AI 模型（OpenAI 兼容网关，如阿里云百炼）──────────────
LLM_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
LLM_BASE_URL = os.environ.get(
    "DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
LLM_MODEL = os.environ.get("DASHSCOPE_MODEL", "qwen-plus")

# ── 数据库（MySQL，可选：论治安全校验/落库需要；缺失时功能降级）──
DB = dict(
    host=os.environ.get("DB_HOST", "localhost"),
    port=int(os.environ.get("DB_PORT", "3306")),
    user=os.environ.get("DB_USER", "root"),
    password=os.environ.get("DB_PASS", ""),
    database=os.environ.get("DB_NAME", "pig_diag_v2"),
    charset="utf8mb4",
)

# ── 路径 ────────────────────────────────────────────────
MODEL_DIR = os.path.join(BASE_DIR, "models")
DATA_DIR = os.path.join(BASE_DIR, "data")
