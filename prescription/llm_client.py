# llm_client.py — LLM 访问统一封装（OpenAI 兼容网关，如阿里百炼）
# 全项目唯一 LLM 调用出口：client 复用 + 参数收敛 + 输出 JSON 提取
# 配置来自 .env（见 config.py），代码中禁止硬编码
import json
import re

from openai import OpenAI

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_ENABLE_THINKING

_client = None  # 复用 OpenAI client，避免每次调用重建

# 流式输出回调：设置后 call_qwen 改用流式请求，逐块回调；不设置则保持原行为
_stream_on_delta = None
_stream_on_start = None
_stream_on_end = None
_stream_on_reasoning = None


def set_stream_callback(on_delta=None, on_start=None, on_end=None, on_reasoning=None):
    """注册流式回调（传 None 关闭流式）。

    on_delta(text)      每个正文增量片段
    on_start()          一次调用开始
    on_end()            一次调用结束
    on_reasoning(text)  思考片段（仅开启思考模式时会有；可选）
    """
    global _stream_on_delta, _stream_on_start, _stream_on_end, _stream_on_reasoning
    _stream_on_delta = on_delta
    _stream_on_start = on_start
    _stream_on_end = on_end
    _stream_on_reasoning = on_reasoning


def get_client():
    """返回（并复用）OpenAI client 实例"""
    global _client
    if _client is None:
        _client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
    return _client


def call_qwen(system_prompt, user_content, temperature=0.3):
    """一次 LLM 对话调用（system + user），返回纯文本回复。

    若已通过 set_stream_callback 注册回调，则改走流式请求并逐块回调；
    网关不支持流式时自动回退普通请求（仅当尚未收到任何片段）。
    """
    client = get_client()
    kwargs = dict(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        temperature=temperature,
        # Qwen3 系默认开启思考模式（显著增加延迟）；由 .env 的
        # DASHSCOPE_ENABLE_THINKING 控制，未设置时默认关闭
        extra_body={"enable_thinking": LLM_ENABLE_THINKING},
    )
    if _stream_on_delta is None:
        resp = client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content

    if _stream_on_start:
        _stream_on_start()
    parts = []
    try:
        stream = client.chat.completions.create(stream=True, **kwargs)
        for chunk in stream:
            if not getattr(chunk, "choices", None):
                continue
            delta = chunk.choices[0].delta
            reason = getattr(delta, "reasoning_content", None) or ""
            if reason and _stream_on_reasoning:
                _stream_on_reasoning(reason)
            text = delta.content or ""
            if text:
                parts.append(text)
                _stream_on_delta(text)
    except Exception:
        if parts:
            raise
        # 网关不支持流式：回退为普通请求，一次性回调全文
        resp = client.chat.completions.create(**kwargs)
        text = resp.choices[0].message.content or ""
        parts.append(text)
        _stream_on_delta(text)
    if _stream_on_end:
        _stream_on_end()
    return "".join(parts)


def extract_json(text):
    """从 LLM 输出中稳健提取 JSON（容忍 markdown 包裹/前后缀文本）"""
    text = text.strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        return json.loads(m.group(0))
    raise json.JSONDecodeError("未找到JSON", text, 0)
