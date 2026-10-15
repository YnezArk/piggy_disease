# config.py — 统一环境配置读取（.env）
# 所有 AI 模型/数据库连接参数集中于此，代码中禁止硬编码
import os
from dotenv import load_dotenv

load_dotenv()

# ── AI 模型（百炼自定义网关，OpenAI 兼容）──────────────
LLM_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
LLM_BASE_URL = os.environ.get(
    "DASHSCOPE_BASE_URL",
    "https://dashscope.aliyuncs.com/compatible-mode/v1",  # 官方网关兜底
)
LLM_MODEL = os.environ.get("DASHSCOPE_MODEL", "qwen-plus")

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
