# 猪咳嗽智能诊疗 — 诊疗决策服务（release）

辨病（咳嗽声→疾病分类）与论治（辨证组方）精简部署包，**不含训练功能**。

## 目录

```
release/
├── api.py            # FastAPI 服务（辨病/论治可分别或一起调用）
├── diagnose.py       # 辨病推理：wav → 疾病诊断（SSLRB/SVM）
├── therapy.py        # 论治引擎：辨证 → 组方 → 安全校验（LLM+RAG）
├── config.py         # 统一配置（读 .env）
├── models/           # 辨病模型（sslr.joblib 六类 v3 / svm_baseline.joblib）
├── data/             # 论治知识库（辨证库/论治库 CSV + 典籍）
├── .env              # 统一环境配置（LLM + 数据库）
├── requirements.txt
└── README.md
```

## 快速开始

```bash
pip install -r requirements.txt
# 编辑 .env：填 DASHSCOPE_API_KEY（论治必填）；DB_* 可选（安全校验/落库，缺失时降级）
python -m uvicorn api:app --host 0.0.0.0 --port 8000
# 文档: http://localhost:8000/docs
```

## API 调用

### ① 论治单独（人工输入辨病 label）

```bash
curl -X POST http://localhost:8000/api/diagnosis \
  -H "Content-Type: application/json" \
  -d '{"disease":"mycoplasma","symptoms":"湿咳、痰多、呼吸粗、食欲下降","temp_c":39.2,"weight_kg":70,"severity":"中度"}'
```

> `disease` 参数 = 辨病模型 label：`app` / `influenza` / `prrs` / `mycoplasma` / `normal` / `other_disease`（也兼容直接传中文病名）；论治内部从数据库查询中文病名后再封装给大模型。

### ② 辨病 + 论治全链路（上传音频）

```bash
curl -X POST http://localhost:8000/api/diagnose-audio \
  -F "file=@cough.wav" \
  -F "symptoms=湿咳、痰多、呼吸粗" \
  -F "temp_c=39.2" -F "weight_kg=70" -F "severity=中度"
```

### ③ 辨病单独（CLI）

```bash
python diagnose.py cough.wav          # 默认 SSLRB
python diagnose.py cough.wav svm      # 切 SVM
```

### ④ 健康检查

```bash
curl http://localhost:8000/api/health
```

## 说明

- **辨病**：恒输出 6 类之一（健康猪只/猪流行性感冒/猪蓝耳病/猪支原体肺炎/猪传染性胸膜肺炎/其他疾病），取置信度最高；`typical_symptoms` 从数据库 `disease.symptoms` 查询（仅展示，DB 不可用时为空）
- **论治**：实际症状由调用方手动传入（`symptoms` 字段）；不传则为空，辨证按缺症状处理
- **数据库**：`DB_*` 配置提供时启用安全校验（剂量区间/十八反）与记录落库；不可用时自动降级（校验仅保留 8 倍上限拦截，不落库）
- 结果由 AI 辅助生成，仅供兽医参考，用药请遵兽医指导
