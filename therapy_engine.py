# therapy_engine.py — 论治引擎（认知层·论治）
# 辨病结果 → [辨证Agent: RAG检索+LLM] → [组方Agent: RAG检索+LLM] → [校验Agent: 规则引擎]
# 依赖: rag_retrieve.py（三库内存检索）、safety.py（剂量/禁忌校验）、.env（DASHSCOPE_API_KEY）
import json
import re

from openai import OpenAI
from rag_retrieve import retrieve, get_all
from safety import calc_dosage, safety_check
from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, DB

# ── LLM 配置（来自 .env，见 config.py）───────────────────
API_KEY, BASE_URL, MODEL = LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
_client = None  # 复用 OpenAI client，避免每次调用重建


def call_qwen(system_prompt, user_content, temperature=0.3):
    global _client
    if _client is None:
        _client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    resp = _client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        temperature=temperature,
    )
    return resp.choices[0].message.content

# ── 知识注入模式 ─────────────────────────────────────────
# True  = 小库全量注入（辨证库9条/论治库14条全给LLM，语义匹配交给大模型，更准）
#        典籍库保持 Top-K 检索（数据大，全量约15k+ token 不划算）
# False = 全部检索 Top-K（旧模式，数据量变大后可回退）
FULL_KB = True


def _extract_json(text):
    """从 LLM 输出中稳健提取 JSON（容忍 markdown 包裹/前后缀文本）"""
    text = text.strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        return json.loads(m.group(0))
    raise json.JSONDecodeError("未找到JSON", text, 0)


# ── 阶段零：查询改写层（LLM 生成检索指令，对齐探讨文档"第一步：检索"）─
# 原始输入(口语化) → LLM 规范化 → 检索查询词 + 体温区间
# 双路检索：① 向量检索(改写后查询) ② Text-to-SQL 精确查辨证库(体温区间+关键词)
QR_SYSTEM = """你是兽医临床数据检索助手。把用户的口语化临床描述改写成适合知识库检索的标准查询词。
知识库字段风格（用这些词汇改写）：
- 咳喘：湿咳/干咳/阵咳/连咳/呼吸粗/呼吸困难/痰多/喘促/张口呼吸
- 排泄物：正常/便秘/稀溏/水样便
- 其他体征：精神差/食欲下降/突发/群发/病程长/反复发作/颈部肿胀
- 证候：邪袭肺卫/疫热壅肺/气阴两伤/风寒束肺/痰湿壅肺
输出严格JSON（无markdown包裹）：
{{
  "syndrome_query": "用于辨证库检索的体征关键词(空格分隔)",
  "classic_query": "用于典籍库检索的查询词(疾病+症状+辨证)",
  "temp_range": "体温区间下界-上界，如 38.5-40，无法判断写 不限"
}}"""


def query_rewrite(disease, symptoms, temp, severity):
    """LLM 生成检索指令。失败时返回 None（调用方用原始拼接兜底）"""
    user = f"疾病：{disease}\n症状：{symptoms}\n体温：{temp}℃\n严重度：{severity}"
    try:
        return _extract_json(call_qwen(QR_SYSTEM, user, temperature=0.0))
    except Exception:
        return None


# 确定性体征词表：口语输入 → 库内词汇（同义词归一，规则式，不依赖LLM）
SIGN_MAP = [
    ('犬类坐', '犬坐'), ('犬坐姿', '犬坐'), ('高温', '高热'), ('发烧', '高热'),
    ('拉稀', '稀溏'), ('腹泻', '稀溏'), ('便稀', '稀溏'), ('水泻', '水样便'),
    ('没精神', '精神差'), ('不吃', '食欲下降'), ('胃口差', '食欲下降'),
    ('咳得厉害', '连咳'), ('咳咳', '咳嗽'), ('喘', '喘促'), ('张口喘', '张口呼吸'),
    ('流鼻涕', '流涕'), ('清鼻涕', '清涕'), ('颈肿', '颈部肿胀'), ('嘴吐沫', '泡沫'),
]
SIGN_KW = ['高热', '低热', '干咳', '湿咳', '阵咳', '连咳', '咳嗽', '喘促', '喘气',
           '张口呼吸', '呼吸困难', '呼吸粗', '呼吸急促', '犬坐', '痰多', '痰黄',
           '流涕', '清涕', '便秘', '稀溏', '水样便', '精神差', '精神萎靡', '食欲下降',
           '突发', '群发', '传播快', '病程长', '反复', '颈部肿胀', '血性泡沫', '泡沫']


def extract_sign_kw(text):
    """从输入文本中确定性提取库内体征词（先同义词归一，再匹配）"""
    t = text
    for src, dst in SIGN_MAP:
        t = t.replace(src, dst)
    return [w for w in SIGN_KW if w in t]


def sql_syndrome_lookup(temp, keywords, extra_kw=None):
    """Text-to-SQL：多关键词OR匹配（每个体征词都参与），返回全部命中规则。
       keywords: LLM改写词 + extra_kw: 规则提取词（并集去重，保证稳定）"""
    import pymysql
    conn = pymysql.connect(**DB)
    cur = conn.cursor()
    # 按非汉字/字母切分（改写词可能带标点，如"高热，犬坐"需拆开）
    tokenized = re.findall(r'[一-鿿A-Za-z0-9]+', keywords)
    merged = []
    for w in list(tokenized) + (extra_kw or []):
        if len(w) >= 2 and w not in merged:
            merged.append(w)
    kw_list = merged[:6]
    if not kw_list:
        conn.close()
        return []
    placeholders = " OR ".join(
        ["(m.cough_type LIKE %s OR m.other_signs LIKE %s OR m.excretion LIKE %s OR m.evidence LIKE %s)"] * len(kw_list))
    args = []
    for w in kw_list:
        args += [f"%{w}%"] * 4
    cur.execute(f'''SELECT s.name, COALESCE(d.name, ''), m.evidence, m.weight, m.cough_type, m.temperature_min, m.temperature_max
      FROM syndrome_mapping m
      JOIN syndrome s ON s.id = m.syndrome_id
      LEFT JOIN disease d ON d.id = m.disease_id
      WHERE (m.temperature_min IS NULL OR %s >= m.temperature_min)
        AND (m.temperature_max IS NULL OR %s <= m.temperature_max)
        AND ({placeholders})
      ORDER BY m.weight DESC''', [temp, temp] + args)
    rows = cur.fetchall()
    conn.close()
    return rows


def rule_cross_check(disease, temp, keyword):
    """确定性交叉验证（非LLM）：全部命中规则逐一对比映射疾病与上游辨病。
       任一规则映射疾病≠上游 → conflict=true（列出全部矛盾规则）"""
    rows = sql_syndrome_lookup(temp, keyword)
    if not rows:
        return {"checked": False, "reason": "无匹配规则，无法交叉验证"}
    conflicts = [f"{r[0]}(对应{r[1]})" for r in rows if r[1] and r[1] != disease]
    return {
        "checked": True,
        "hits": [{"syndrome": r[0], "disease": r[1] or "未标注", "weight": r[3]}
                 for r in rows],
        "upstream_disease": disease,
        "conflict": len(conflicts) > 0,
        "reason": (f"规则库命中 {len(rows)} 条，其中 {conflicts} 与上游辨病'{disease}'不一致，"
                   f"建议核实辨病结果" if conflicts else
                   f"规则库命中 {len(rows)} 条，映射疾病均与上游辨病一致"),
    }


# ── 阶段一：辨证Agent ──────────────────────────────────────
SX_SYSTEM = """你是资深中兽医辨证专家，精通猪呼吸道疾病三期辨证论治
（前期邪袭肺卫→中期疫热壅肺→后期气阴两伤）。
你收到以下检索自权威资料的片段，必须基于它们辨证，不可虚构；
检索为空时必须在结果中注明"缺检索依据"。
{sym_docs}
{med_docs}

⚠️ 重要原则（必须遵守）：
1. 上游"辨病结果"只是参考信息，可能不准确——辨证必须以临床症状体征和检索证据为准
2. 中医"同病异证"：同一疾病不同阶段/体质可呈不同证候；同一证候也可出现在不同疾病
3. 若症状体征与辨病结果矛盾（如辨病为支原体肺炎但呈突发高热40℃+、群发，典型流感表现），
   必须按症状判定证候，并在 disease_conflict 中明确指出矛盾与建议修正方向
4. 不得为了迎合辨病结果而扭曲辨证
5. 【主症优先】咳嗽类型、体温、呼吸表现是定证主症，精神/食欲/排泄物是兼症（佐证程度、定病势），
   不得因单一兼症（如偶见稀溏）推翻主症指向的证候——需主症+多个兼症共同支持才可判定
6. 【特异体征优先】犬坐姿势、张口呼吸、口鼻血性/泡沫样液体是肺气壅闭的重症特异体征，
   高度指向疫热壅肺（传染性胸膜肺炎/猪肺疫），其判定权重高于"突发高热"等泛化体征；
   同时出现高热与犬坐时，按重症特异体征定证，不得判为前期表证
7. 你收到的是辨证库全部规则（已附【来源】标签），逐一与输入匹配，选出与主症最吻合的规则；
   SQL精确命中仅为候选参考，最终以全量规则+特异体征核对为准

输出严格JSON（无markdown包裹）：
{{
  "stage": "前期/中期/后期",
  "syndrome": "证型名称",
  "principle": "治则治法",
  "evidence": ["依据1", "依据2"],
  "references": ["引用出处（取自检索片段）"],
  "disease_conflict": {{
    "upstream_disease": "上游辨病结果",
    "evidence_disease": "根据症状体征和检索证据最符合的疾病",
    "conflict": true/false,
    "reason": "矛盾说明；无矛盾时写'症状体征与辨病结果一致'"
  }}
}}"""


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
    sx = _extract_json(call_qwen(
        SX_SYSTEM.format(sym_docs=sym_docs, med_docs=med_docs),
        user, temperature=0.0))  # 辨证求确定性，温度0消除随机漂移
    sx['rule_cross_check'] = cross_check or {}          # None 兜底（SQL异常时）
    if sx.get('disease_conflict') is None:              # LLM 输出 null 时兜底
        sx['disease_conflict'] = {'upstream_disease': disease, 'evidence_disease': '',
                                  'conflict': False, 'reason': 'LLM未返回冲突检查'}
    return sx


# ── 阶段二：组方Agent ──────────────────────────────────────
RX_SYSTEM = """你是中兽药师、方剂学专家。
你收到以下检索自权威资料的片段（基础方剂与典籍条文），必须基于它们组方，不可虚构；
检索为空时必须在结果中注明"缺检索依据"。
{formula_docs}
{med_docs}
结合猪只参数（体重/月龄/病情严重度）加减化裁。
剂量必须是具体数字（克），由你给出基础剂量，换算由校验环节完成。
输出严格JSON（无markdown包裹）：
{{
  "base_formula": "基础方剂名",
  "herbs": [{{"name": "药材", "dosage_g": 15, "role": "君/臣/佐/使"}}],
  "add_notes": ["加减说明"],
  "preparation": "用法（如按500g饲料混饲）",
  "course": "疗程",
  "contraindications": ["禁忌"],
  "references": ["引用出处（取自检索片段）"]
}}"""


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
    return _extract_json(call_qwen(
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
