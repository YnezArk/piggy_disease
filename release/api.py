# -*- coding: utf-8 -*-
"""
api.py — 诊疗决策 API 服务（辨病 / 论治 可分别或一起调用）

端点：
  POST /api/diagnosis         论治单独：疾病+症状 → 辨证组方（人工输入辨病结果）
  POST /api/diagnose-audio    辨病+论治：上传 wav → 辨病 → 桥接 → 辨证组方（全链路）
  GET  /api/health            健康检查

启动：python -m uvicorn api:app --host 0.0.0.0 --port 8000
文档：http://localhost:8000/docs
"""
import json
import os
import tempfile

import pymysql
from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import Optional

from config import DB
from diagnose import diagnose as predict_diagnose, load_model
from therapy import treatment_pipeline

app = FastAPI(title="猪咳嗽诊疗决策 API", version="1.0.0")


# ── 请求模型 ──────────────────────────────────────────────
class DiagnosisRequest(BaseModel):
    disease: str = Field(..., description="辨病模型 label（app/influenza/prrs/mycoplasma/normal/other_disease），兼容中文病名")
    confidence: Optional[float] = Field(0.0, description="辨病置信度0-1（可选）")
    symptoms: str = Field(..., description="实际临床症状（手动输入）")
    temp_c: float = Field(..., description="体温℃")
    weight_kg: float = Field(..., description="体重kg")
    severity: str = Field("中度", description="病情：轻度/中度/重度")
    pig_house: Optional[str] = Field("", description="猪舍编号（可选）")
    pig_extra: Optional[str] = Field("", description="补充信息，如月龄（可选）")


# ── 落库（可选：DB 不可用时降级跳过，不阻塞主流程）────────────
def _save_record(req: DiagnosisRequest, result: dict,
                 label: str = None, file_source: str = None) -> int:
    try:
        conn = pymysql.connect(**DB)
        cur = conn.cursor()
        disease_id = None
        if label:
            cur.execute("SELECT id FROM disease WHERE label=%s", (label,))
            row = cur.fetchone()
            disease_id = row[0] if row else None
        cur.execute(
            "INSERT INTO diagnosis_record (pig_house, model_label, disease_id, confidence, "
            "temp_c, file_source, created_at) VALUES (%s, %s, %s, %s, %s, %s, NOW())",
            (req.pig_house, label or req.disease, disease_id, req.confidence, req.temp_c, file_source))
        diag_id = cur.lastrowid
        sx, rx, vf = result['syndrome'], result['prescription'], result['verification']
        cur.execute("SELECT id FROM syndrome WHERE name=%s", (sx.get('syndrome', ''),))
        row = cur.fetchone()
        syndrome_id = row[0] if row else None
        cur.execute(
            "INSERT INTO prescription_record (diagnosis_id, syndrome_id, herbs_json, usage_method, "
            "course, safety_approved, safety_report, llm_raw, references_json, created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())",
            (diag_id, syndrome_id, json.dumps(rx.get('herbs', []), ensure_ascii=False),
             rx.get('preparation', ''), rx.get('course', ''),
             1 if vf['safe'] else 0, json.dumps(vf, ensure_ascii=False),
             json.dumps(rx, ensure_ascii=False), json.dumps(rx.get('references', []), ensure_ascii=False)))
        rx_id = cur.lastrowid
        conn.commit()
        conn.close()
        return rx_id
    except Exception:
        return 0  # 落库失败降级：不影响结果返回


def _run_therapy(req: DiagnosisRequest) -> dict:
    """论治统一入口"""
    return treatment_pipeline(
        disease=req.disease, symptoms=req.symptoms, temp=req.temp_c,
        weight=req.weight_kg, severity=req.severity,
        pig_extra=req.pig_extra or f"体重{req.weight_kg}kg")


@app.post("/api/diagnosis")
def diagnose(req: DiagnosisRequest):
    """论治单独调用：手动输入辨病结果 + 实际症状 → 辨证组方"""
    try:
        result = _run_therapy(req)
        rx_id = _save_record(req, result)
        return {"code": 0, "trace_id": f"RX-{rx_id}",
                "syndrome": result['syndrome'], "prescription": result['prescription'],
                "verification": result['verification'],
                "disclaimer": "本结果由AI辅助生成，仅供兽医参考，用药请遵兽医指导"}
    except Exception as e:
        return {"code": 1, "message": f"诊疗失败: {e}"}


@app.post("/api/diagnose-audio")
async def diagnose_audio(
        file: UploadFile = File(..., description="咳嗽音频 wav"),
        symptoms: str = Form("", description="实际临床症状（手动输入；缺省为空）"),
        temp_c: float = Form(39.0, description="体温℃（缺省 39.0）"),
        weight_kg: float = Form(70.0, description="体重kg"),
        severity: str = Form("中度", description="病情：轻度/中度/重度"),
        pig_house: str = Form("", description="猪舍编号（可选）"),
        pig_extra: str = Form("", description="补充信息，如月龄（可选）"),
        model_name: str = Form("sslr", description="辨病模型：sslr/svm")):
    """辨病+论治全链路：wav → 辨病 → 桥接 → 辨证组方"""
    try:
        suffix = os.path.splitext(file.filename or "upload.wav")[1] or ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name
        try:
            dx = predict_diagnose(tmp_path, model_name=model_name)
        finally:
            os.unlink(tmp_path)

        # 桥接：disease 传辨病 label（论治内部查 DB 转中文名）；typical_symptoms 仅展示；症状只用手动输入
        req = DiagnosisRequest(
            disease=dx["label"], confidence=dx["confidence"],
            symptoms=symptoms, temp_c=temp_c, weight_kg=weight_kg,
            severity=severity, pig_house=pig_house, pig_extra=pig_extra)
        result = _run_therapy(req)
        rx_id = _save_record(req, result, label=dx["label"],
                             file_source=f"upload/{file.filename or 'audio.wav'}")
        return {"code": 0, "trace_id": f"RX-{rx_id}", "diagnosis": dx,
                "syndrome": result['syndrome'], "prescription": result['prescription'],
                "verification": result['verification'],
                "disclaimer": "本结果由AI辅助生成，仅供兽医参考，用药请遵兽医指导"}
    except Exception as e:
        return {"code": 1, "message": f"诊疗失败: {e}"}


@app.get("/api/health")
def health():
    return {"status": "ok"}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
