# test_qwen.py — 网关连通性测试（配置全部来自 .env，见 config.py）
from dotenv import load_dotenv

load_dotenv()

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, check_env

missing = check_env()
if missing:
    print("❌ 缺少环境配置:", "，".join(missing))
    print("   检查项目根目录 .env 文件")
    exit(1)

from openai import OpenAI

client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

print(f"网关: {LLM_BASE_URL}")
print(f"模型: {LLM_MODEL}")

try:
    resp = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": "你是专业兽医,猪咳嗽三天，体温39.8℃，痰多，请用一句话给个初步判断"}],
    )
    print(resp.choices[0].message.content)
except Exception as e:
    print("❌ 调用失败：")
    print("  HTTP", getattr(e, "status_code", "?"))
    print("  body:", getattr(e, "body", str(e)))
