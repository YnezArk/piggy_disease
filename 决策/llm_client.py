# llm_client.py — LLM 访问统一封装（OpenAI 兼容网关，如阿里百炼）
# 全项目唯一 LLM 调用出口：client 复用 + 参数收敛 + 输出 JSON 提取
# 配置来自 .env（见 config.py），代码中禁止硬编码
import json
import re

from openai import OpenAI

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

_client = None  # 复用 OpenAI client，避免每次调用重建


def get_client():
    """返回（并复用）OpenAI client 实例"""
    global _client
    if _client is None:
        _client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
    return _client


def call_qwen(system_prompt, user_content, temperature=0.3):
    """一次 LLM 对话调用（system + user），返回纯文本回复"""
    resp = get_client().chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        temperature=temperature,
    )
    return resp.choices[0].message.content


def extract_json(text):
    """从 LLM 输出中稳健提取 JSON（容忍 markdown 包裹/前后缀文本）"""
    text = text.strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        return json.loads(m.group(0))
    raise json.JSONDecodeError("未找到JSON", text, 0)
