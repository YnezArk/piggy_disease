# api_server.py — 诊疗决策板块 API 服务（对接整合板块）
# 启动: D:/SDK/Python314/python.exe -m uvicorn api_server:app --host 0.0.0.0 --port 8000
# 文档: http://localhost:8000/docs
import json
import pymysql
from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Optional

from therapy_engine import treatment_pipeline
from config import DB

app = FastAPI(title="诊疗决策板块 API", version="0.1.0")


# ── 请求/响应模型 ──────────────────────────────────────────
class DiagnosisRequest(BaseModel):
    disease: str = Field(..., description="辨病模型输出，如：猪支原体肺炎")
    confidence: Optional[float] = Field(0.0, description="辨病置信度0-1")
    symptoms: str = Field(..., description="临床症状描述")
    temp_c: float = Field(..., description="体温℃")
    weight_kg: float = Field(..., description="体重kg")
    severity: str = Field("中度", description="病情：轻度/中度/重度")
    pig_house: Optional[str] = Field("", description="猪舍编号")
    pig_extra: Optional[str] = Field("", description="补充信息（月龄等）")


def _save_record(req: DiagnosisRequest, result: dict) -> int:
    """辨病记录 + 处方记录落库，返回处方记录ID"""
    conn = pymysql.connect(**DB)
    cur = conn.cursor()
    # 1. 辨病记录
    cur.execute(
        "INSERT INTO diagnosis_record (pig_house, model_label, confidence, temp_c, created_at) "
        "VALUES (%s, %s, %s, %s, NOW())",
        (req.pig_house, req.disease, req.confidence, req.temp_c))
    diag_id = cur.lastrowid
    # 2. 处方记录（syndrome_id 按证候名查外键，查不到则 NULL）
    sx = result['syndrome']
    rx = result['prescription']
    vf = result['verification']
    cur.execute("SELECT id FROM syndrome WHERE name=%s", (sx.get('syndrome', ''),))
    row = cur.fetchone()
    syndrome_id = row[0] if row else None
    cur.execute(
        "INSERT INTO prescription_record "
        "(diagnosis_id, syndrome_id, herbs_json, usage_method, course, safety_approved, "
        "safety_report, llm_raw, references_json, created_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())",
        (diag_id,
         syndrome_id,
         json.dumps(rx.get('herbs', []), ensure_ascii=False),
         rx.get('preparation', ''), rx.get('course', ''),
         1 if vf['safe'] else 0,
         json.dumps(vf, ensure_ascii=False),
         json.dumps(rx, ensure_ascii=False),
         json.dumps(rx.get('references', []), ensure_ascii=False)))
    rx_id = cur.lastrowid
    conn.commit()
    conn.close()
    return rx_id


@app.post("/api/diagnosis")
def diagnose(req: DiagnosisRequest):
    """辨病结果 → 辨证 → 组方 → 校验 → 落库 → 返回完整诊疗方案"""
    try:
        result = treatment_pipeline(
            disease=req.disease,
            symptoms=req.symptoms,
            temp=req.temp_c,
            weight=req.weight_kg,
            severity=req.severity,
            pig_extra=req.pig_extra or f"体重{req.weight_kg}kg",
        )
        rx_id = _save_record(req, result)
        return {
            "code": 0,
            "trace_id": f"RX-{rx_id}",
            "syndrome": result['syndrome'],
            "prescription": result['prescription'],
            "verification": result['verification'],
            "disclaimer": "本结果由AI辅助生成，仅供兽医参考，用药请遵兽医指导",
        }
    except Exception as e:
        return {"code": 1, "message": f"诊疗失败: {e}"}


@app.get("/api/health")
def health():
    return {"status": "ok"}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
