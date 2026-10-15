# therapy_engine.py — 论治引擎（认知层·论治）总调度
# 辨病结果 → [辨证Agent: RAG检索+LLM] → [组方Agent: RAG检索+LLM] → [校验Agent: 规则引擎]
#
# 模块化拆分（逻辑不变，仅按职责分文件）：
#   llm_client.py  — LLM 访问统一封装（client复用/call_qwen/JSON提取）
#   prompts.py     — 三套 Agent 系统提示词
#   kb_lookup.py   — 确定性检索：体征词归一 / SQL辨证检索 / 规则交叉验证
#   rag_retrieve.py— 三库内存向量检索（retrieve/get_all）
#   safety.py      — 剂量/禁忌校验规则引擎
#   config.py      — .env 统一配置
import json

from llm_client import call_qwen, extract_json
from prompts import QR_SYSTEM, SX_SYSTEM, RX_SYSTEM
from kb_lookup import extract_sign_kw, sql_syndrome_lookup, rule_cross_check
from rag_retrieve import retrieve, get_all
from safety import calc_dosage, safety_check

# ── 知识注入模式 ─────────────────────────────────────────
# True  = 小库全量注入（辨证库9条/论治库14条全给LLM，语义匹配交给大模型，更准）
#        典籍库保持 Top-K 检索（数据大，全量约15k+ token 不划算）
# False = 全部检索 Top-K（旧模式，数据量变大后可回退）
FULL_KB = True


# ── 阶段零：查询改写层（LLM 生成检索指令，对齐探讨文档"第一步：检索"）─
def query_rewrite(disease, symptoms, temp, severity):
    """LLM 生成检索指令。失败时返回 None（调用方用原始拼接兜底）"""
    user = f"疾病：{disease}\n症状：{symptoms}\n体温：{temp}℃\n严重度：{severity}"
    try:
        return extract_json(call_qwen(QR_SYSTEM, user, temperature=0.0))
    except Exception:
        return None


# ── 阶段一：辨证Agent ──────────────────────────────────────
def syndrome_stage(disease, symptoms, temp, weight, severity, q=None):
    """辨病结果 + 症状体征 → 证型/治则
       q: query_rewrite 的检索指令；None 时用原始拼接兜底"""
    # ① 知识注入：FULL_KB=全量辨证库（LLM全局权衡）| 否则检索 Top-K
    if q:
        med_query = q.get('classic_query') or f"{disease} {symptoms} 辨证 治则"
    else:
        med_query = f"{disease} {symptoms} 辨证 治则"
    if FULL_KB:
        sym_docs = "\n".join(get_all('symptom_disease'))     # 9条全量
    else:
        sym_query = q.get('syndrome_query') if q else f"{disease} {symptoms} 体温{temp}"
        sym_docs = "\n".join(retrieve('symptom_disease', sym_query, k=3))
    med_docs = "\n".join(retrieve('tcm_classics', med_query, k=5))

    # ② Text-to-SQL 精确检索：改写词 + 规则提取词并集（改写失败时仍有稳定体征词）
    sql_hits, cross_check = "", None
    kw_llm = q.get('syndrome_query', '') if q and q.get('syndrome_query') else symptoms
    kw_rule = extract_sign_kw(symptoms)
    try:
        rows = sql_syndrome_lookup(temp, kw_llm, kw_rule)
        if rows:
            sql_hits = "\n".join(
                f"[SQL命中] 证候：{n}，对应疾病：{d or '未标注'}（权重{w}），咳喘特征：{c or ''}，"
                f"体温区间：{tmin or '不限'}~{tmax or '不限'}，依据：{e or ''}"
                for n, d, e, w, c, tmin, tmax in rows)
        # ③ 确定性交叉验证：全部命中规则 vs 上游辨病结果（改写词+规则词并集）
        cross_check = rule_cross_check(disease, temp, kw_llm + ' ' + ' '.join(kw_rule))
    except Exception:
        pass  # SQL 检索失败不影响主流程

    user = (f"辨病结果（参考，可能不准确）：{disease}\n临床症状：{symptoms}\n体温：{temp}℃\n"
            f"猪只信息：体重{weight}kg，{severity}病情\n"
            + (f"\nSQL精确检索候选（仅供参考，需与全量规则核对特异体征）：\n{sql_hits}" if sql_hits else "") +
            (f"\n规则交叉验证：{cross_check['reason']}"
             if cross_check and cross_check['checked'] else "") +
            "\n请辨证分型（以全量规则+特异体征为准，若与辨病结果矛盾必须指出）。")
    sx = extract_json(call_qwen(
        SX_SYSTEM.format(sym_docs=sym_docs, med_docs=med_docs),
        user, temperature=0.0))  # 辨证求确定性，温度0消除随机漂移
    sx['rule_cross_check'] = cross_check or {}          # None 兜底（SQL异常时）
    if sx.get('disease_conflict') is None:              # LLM 输出 null 时兜底
        sx['disease_conflict'] = {'upstream_disease': disease, 'evidence_disease': '',
                                  'conflict': False, 'reason': 'LLM未返回冲突检查'}
    return sx


# ── 阶段二：组方Agent ──────────────────────────────────────
def formula_stage(sx_result, pig_info):
    """辨证结果 + 猪只信息 → 处方"""
    # 论治库：FULL_KB=全量14条（含迎甘组方/清肺散/麻杏石甘散/银翘散等全部候选，LLM自选）
    #         否则检索 Top-K
    if FULL_KB:
        formula_docs = "\n".join(get_all('disease_formula'))
    else:
        q = f"{sx_result.get('syndrome', '')} {sx_result.get('principle', '')} 组方"
        formula_docs = "\n".join(retrieve('disease_formula', q, k=3))
    med_docs = "\n".join(retrieve('tcm_classics', "方剂 剂量 禁忌 加减", k=5))
    user = f"辨证结果：{json.dumps(sx_result, ensure_ascii=False)}\n猪只信息：{pig_info}\n请开具组方。"
    return extract_json(call_qwen(
        RX_SYSTEM.format(formula_docs=formula_docs, med_docs=med_docs),
        user, temperature=0.5))


# ── 阶段三：校验Agent（规则引擎）────────────────────────────
def verify_stage(rx, weight, severity):
    """安全校验。拌料/混饲类（整方给药）不逐味体重换算；
       灌服/煎汤类按体重换算并提示单次量。"""
    prep = rx.get('preparation', '')
    is_drench = ('灌服' in prep) or ('煎' in prep) or ('汤' in prep)
    herbs = []
    for h in rx.get('herbs', []):
        entry = {'name': h['name'], 'dosage_g': float(h.get('dosage_g', 0))}
        if is_drench:
            entry['dosage_g'] = calc_dosage(entry['dosage_g'], weight, severity)
        herbs.append(entry)
    report = safety_check({'herbs': herbs})
    report['note'] = '灌服类已按体重系数换算' if is_drench else '拌料类按整方剂量校验'
    return report


# ── 主流水线 ───────────────────────────────────────────────
def treatment_pipeline(disease, symptoms, temp, weight, severity, pig_extra=""):
    """输入辨病结果 → 完整论治链路
       阶段0: LLM查询改写（生成检索指令）→ 双路检索（向量+SQL）
       阶段1: 辨证Agent → 阶段2: 组方Agent → 阶段3: 校验Agent"""
    print("[0/4] 查询改写（LLM生成检索指令）...")
    q = query_rewrite(disease, symptoms, temp, severity)
    print("      检索词:", (q or {}).get('syndrome_query', '（改写失败，用原始输入）'))

    print("[1/4] 辨证Agent（向量+SQL双路检索）...")
    sx = syndrome_stage(disease, symptoms, temp, weight, severity, q)
    print("      证型:", sx.get('syndrome'), "| 治则:", sx.get('principle'))

    print("[2/4] 组方Agent（RAG检索）...")
    pig_info = f"体重{weight}kg，{severity}病情，{pig_extra}"
    rx = formula_stage(sx, pig_info)
    print("      基础方:", rx.get('base_formula'), "| 药材数:", len(rx.get('herbs', [])))

    print("[3/4] 校验Agent（规则引擎）...")
    report = verify_stage(rx, weight, severity)
    print("      安全:", report['safe'], "| 拦截:", report.get('errors') or "无",
          "| 提示:", report.get('warnings') or "无")

    return {
        'syndrome': sx,
        'prescription': rx,
        'verification': report,
    }


if __name__ == '__main__':
    result = treatment_pipeline(
        disease="支原体肺炎（辨病模型输出）",
        symptoms="湿咳、痰多、呼吸粗，食欲下降",
        temp=39.2,
        weight=70,
        severity="中度",
        pig_extra="4月龄育肥猪",
    )
    print("\n=== 最终结果 ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))
