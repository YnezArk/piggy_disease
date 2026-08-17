# api_server.py — 诊疗决策板块 API 服务（对接整合板块）
# 启动: D:/SDK/Python314/python.exe -m uvicorn api_server:app --host 0.0.0.0 --port 8000
# 文档: http://localhost:8000/docs
import json
import os
import sys
import tempfile

import pymysql
from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import Optional

from therapy_engine import treatment_pipeline
from config import DB

# 辨病模块（位于辨病/，经 bridge 解耦调用）
# 注：predict.diagnose 以别名导入——下方端点函数同名 diagnose，避免覆盖
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "辨病"))
from predict import diagnose as predict_diagnose, load_model
from bridge import build_therapy_input, call_therapy

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


def _save_record(req: DiagnosisRequest, result: dict,
                 label: str = None, file_source: str = None) -> int:
    """辨病记录 + 处方记录落库，返回处方记录ID

    label/file_source 由音频入口（/api/diagnose-audio）传入；
    disease_id 按 label 解析（disease.label 与辨病模型标签一致）。
    """
    conn = pymysql.connect(**DB)
    cur = conn.cursor()
    # 1. 辨病记录
    disease_id = None
    if label:
        cur.execute("SELECT id FROM disease WHERE label=%s", (label,))
        row = cur.fetchone()
        disease_id = row[0] if row else None
    cur.execute(
        "INSERT INTO diagnosis_record (pig_house, model_label, disease_id, confidence, "
        "temp_c, file_source, created_at) VALUES (%s, %s, %s, %s, %s, %s, NOW())",
        (req.pig_house, label or req.disease, disease_id, req.confidence,
         req.temp_c, file_source))
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


@app.post("/api/diagnose-audio")
async def diagnose_audio(
        file: UploadFile = File(..., description="咳嗽音频 wav"),
        temp_c: float = Form(39.0, description="体温℃（缺省 39.0）"),
        weight_kg: float = Form(70.0, description="体重kg"),
        severity: str = Form("中度", description="病情：轻度/中度/重度"),
        symptoms: str = Form("", description="手动输入实际症状（缺省为空，不自动用辨病典型症状）"),
        pig_house: str = Form("", description="猪舍编号"),
        pig_extra: str = Form("", description="补充信息（月龄等）"),
        model_name: str = Form("sslr", description="辨病模型：sslr/svm")):
    """音频 → 辨病 → 辨证 → 组方 → 校验 → 落库 → 完整诊疗方案（全链路）"""
    try:
        # 1. 保存临时音频 → 辨病
        suffix = os.path.splitext(file.filename or "upload.wav")[1] or ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name
        dx = predict_diagnose(tmp_path, model_name=model_name)
        os.unlink(tmp_path)

        # 2. 桥接 → 论治
        therapy, meta = build_therapy_input(
            dx, temp_c=temp_c, weight_kg=weight_kg, severity=severity,
            symptoms=symptoms or None, pig_extra=pig_extra)
        result = call_therapy(therapy)

        # 3. 落库（label/file_source 随音频入口记录）
        req = DiagnosisRequest(
            disease=therapy["disease"], confidence=meta["confidence"],
            symptoms=therapy["symptoms"], temp_c=temp_c, weight_kg=weight_kg,
            severity=severity, pig_house=pig_house, pig_extra=pig_extra)
        rx_id = _save_record(req, result, label=meta["label"],
                             file_source=f"upload/{file.filename or 'audio.wav'}")

        return {
            "code": 0,
            "trace_id": f"RX-{rx_id}",
            "diagnosis": dx,
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
