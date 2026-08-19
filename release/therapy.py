# -*- coding: utf-8 -*-
"""
therapy.py — 论治引擎（辨病结果 + 症状 → 辨证组方，无训练功能）
合并自：llm_client / prompts / kb_lookup / rag_retrieve / safety / therapy_engine

流程：查询改写(LLM) → 双路检索(向量+SQL) → 辨证Agent(LLM) → 组方Agent(LLM) → 校验Agent(规则引擎)

用法：
  from therapy import treatment_pipeline
  result = treatment_pipeline(disease="app", symptoms="湿咳、痰多、呼吸粗",
                              temp=39.2, weight=70, severity="中度")
  # disease 参数 = 辨病模型 label（app/influenza/prrs/mycoplasma/normal/other_disease；
  #                也兼容中文病名），内部查 DB disease 表得到中文名后再封装给 LLM
  # → {'syndrome': {...}, 'prescription': {...}, 'verification': {...}}

依赖：.env 的 DASHSCOPE_API_KEY（LLM）；MySQL（安全校验/规则检索/疾病名映射，缺失时降级）
"""
import csv
import hashlib
import json
import math
import os
import re

import jieba
import pymysql
from openai import OpenAI

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, DB, DATA_DIR

# ════════════════════════════════════════════════════════════
# 1. LLM 访问封装
# ════════════════════════════════════════════════════════════
_client = None


def get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
    return _client


def call_qwen(system_prompt, user_content, temperature=0.3):
    resp = get_client().chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "system", "content": system_prompt},
                  {"role": "user", "content": user_content}],
        temperature=temperature)
    return resp.choices[0].message.content


def extract_json(text):
    text = text.strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        return json.loads(m.group(0))
    raise json.JSONDecodeError("未找到JSON", text, 0)


_disease_name_cache = None  # {label: 中文名}


def lookup_disease_name(key):
    """label（或中文名）→ DB disease 表中文名；DB 不可用/查不到时原样返回"""
    global _disease_name_cache
    if _disease_name_cache is None:
        _disease_name_cache = {}
        try:
            conn = _db_conn()
            cur = conn.cursor()
            cur.execute("SELECT label, name FROM disease WHERE label IS NOT NULL")
            for label, name in cur.fetchall():
                _disease_name_cache[label] = name
            conn.close()
        except Exception:
            pass
    return _disease_name_cache.get(key, key)


# ════════════════════════════════════════════════════════════
# 2. Agent 系统提示词
# ════════════════════════════════════════════════════════════
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


# ════════════════════════════════════════════════════════════
# 3. 内存 RAG 检索（辨证库/论治库 CSV + 典籍 txt，余弦相似）
# ════════════════════════════════════════════════════════════
DIM = 512
_DB = None  # {name: [(doc, source, vec), ...]}


def _embed(text):
    v = [0.0] * DIM
    for w in jieba.cut(text):
        if len(w.strip()) < 2:
            continue
        h = int(hashlib.md5(w.encode('utf-8')).hexdigest()[:8], 16)
        v[h % DIM] += 1.0
    norm = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / norm for x in v]


def _cos(a, b):
    return sum(x * y for x, y in zip(a, b))


def _load():
    global _DB
    _DB = {'symptom_disease': [], 'disease_formula': [], 'tcm_classics': []}
    base = os.path.join(DATA_DIR, 'kg')
    for fname, key, fmt in [
        ('symptom_disease.csv', 'symptom_disease',
         lambda r: (f"体温{r['temperature_min'] or '不限'}~{r['temperature_max'] or '不限'}℃，"
                    f"咳喘：{r['cough_type']}，排泄物：{r['excretion']}，其他体征：{r['other_signs']} → "
                    f"证候：{r['syndrome']}，疾病：{r['disease'] or '无'}，鉴别依据：{r['evidence']}")),
        ('disease_formula.csv', 'disease_formula',
         lambda r: (f"证候/疾病：{r['disease']} → 基础方剂：{r['base_formula']}，"
                    f"组成：{r['herbs']}，加减：{r['add_rule']}，用法：{r['usage']}，"
                    f"疗程：{r['course']}，禁忌：{r['contraindication']}，出处：{r['reference']}"))]:
        p = os.path.join(base, fname)
        if os.path.exists(p):
            with open(p, encoding='utf-8-sig') as f:
                for row in csv.DictReader(f):
                    doc = fmt(row)
                    _DB[key].append((doc, '辨证库' if key == 'symptom_disease' else '论治库', _embed(doc)))
    for root, _, files in os.walk(os.path.join(DATA_DIR, 'rag', 'classics')):
        for fn in files:
            if not fn.endswith(('.txt', '.md')):
                continue
            friendly = f"典籍·{fn.replace('.txt', '').replace('.md', '')}"
            with open(os.path.join(root, fn), encoding='utf-8') as fh:
                text = fh.read()
            for chunk in [p.strip() for p in text.split('\n') if len(p.strip()) > 30]:
                _DB['tcm_classics'].append((chunk, friendly, _embed(chunk)))


def retrieve(name, query, k=3):
    if _DB is None:
        _load()
    qv = _embed(query)
    scored = sorted(((_cos(doc_vec, qv), doc, src) for doc, src, doc_vec in _DB[name]),
                    key=lambda x: -x[0])
    return [f"【来源：{src}】{doc}" for score, doc, src in scored[:k] if score > 0]


def get_all(name):
    """小库全量注入（辨证库/论治库全给 LLM 做全局判断）"""
    if _DB is None:
        _load()
    return [f"【来源：{src}】{doc}" for doc, src, _ in _DB[name]]


# ════════════════════════════════════════════════════════════
# 4. 确定性知识检索与规则交叉验证（非 LLM，依赖 MySQL）
# ════════════════════════════════════════════════════════════
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


def _db_conn():
    return pymysql.connect(**DB)


def extract_sign_kw(text):
    t = text
    for src, dst in SIGN_MAP:
        t = t.replace(src, dst)
    return [w for w in SIGN_KW if w in t]


def sql_syndrome_lookup(temp, keywords, extra_kw=None):
    """Text-to-SQL 多关键词 OR 匹配辨证库；DB 不可用时返回 []（降级）"""
    try:
        conn = _db_conn()
    except Exception:
        return []
    cur = conn.cursor()
    tokenized = re.findall(r'[一-鿿A-Za-z0-9]+', keywords)
    merged = []
    for w in list(tokenized) + (extra_kw or []):
        if len(w) >= 2 and w not in merged:
            merged.append(w)
    kw_list = merged[:6]
    if not kw_list:
        conn.close()
        return []
    ph = " OR ".join(
        ["(m.cough_type LIKE %s OR m.other_signs LIKE %s OR m.excretion LIKE %s OR m.evidence LIKE %s)"] * len(kw_list))
    args = []
    for w in kw_list:
        args += [f"%{w}%"] * 4
    try:
        cur.execute(f'''SELECT s.name, COALESCE(d.name, ''), m.evidence, m.weight, m.cough_type, m.temperature_min, m.temperature_max
          FROM syndrome_mapping m
          JOIN syndrome s ON s.id = m.syndrome_id
          LEFT JOIN disease d ON d.id = m.disease_id
          WHERE (m.temperature_min IS NULL OR %s >= m.temperature_min)
            AND (m.temperature_max IS NULL OR %s <= m.temperature_max)
            AND ({ph})
          ORDER BY m.weight DESC''', [temp, temp] + args)
        rows = cur.fetchall()
    except Exception:
        rows = []
    conn.close()
    return rows


_disease_aliases = None


def _load_disease_aliases():
    global _disease_aliases
    if _disease_aliases is not None:
        return
    try:
        conn = _db_conn()
    except Exception:
        _disease_aliases = {}
        return
    cur = conn.cursor()
    cur.execute("SELECT name, COALESCE(alias, '') FROM disease")
    _disease_aliases = {}
    for name, alias in cur.fetchall():
        s = {name}
        for a in alias.replace('，', ',').split(','):
            a = a.strip()
            if a:
                s.add(a)
        _disease_aliases[name] = s
    conn.close()


def _same_disease(a, b):
    if not a or not b:
        return False
    if a == b:
        return True
    _load_disease_aliases()
    for aliases in _disease_aliases.values():
        if a in aliases and b in aliases:
            return True
    return False


def rule_cross_check(disease, temp, keyword):
    """确定性交叉验证：全部命中规则 vs 上游辨病（别名归一）"""
    rows = sql_syndrome_lookup(temp, keyword)
    if not rows:
        return {"checked": False, "reason": "无匹配规则，无法交叉验证"}
    same = [f"{r[0]}(对应{r[1]})" for r in rows if r[1] and _same_disease(r[1], disease)]
    others = [f"{r[0]}(对应{r[1]})" for r in rows if r[1] and not _same_disease(r[1], disease)]
    if same:
        reason = (f"规则库命中 {len(rows)} 条，其中 {len(same)} 条与上游辨病'{disease}'一致"
                  f"（{same[0]}）" +
                  (f"，另 {len(others)} 条指向其他疾病（{others}，可能混合感染或症状交叉）"
                   if others else ""))
    else:
        reason = (f"规则库命中 {len(rows)} 条，均未映射到上游辨病'{disease}'"
                  f"（命中：{others}），与上游不一致，建议核实辨病结果")
    return {"checked": True,
            "hits": [{"syndrome": r[0], "disease": r[1] or "未标注", "weight": r[3]} for r in rows],
            "upstream_disease": disease, "conflict": len(same) == 0, "reason": reason}


# ════════════════════════════════════════════════════════════
# 5. 安全校验（确定性规则，非 LLM；DB 缺失时跳过禁忌检查）
# ════════════════════════════════════════════════════════════
WEIGHT_COEF = {(0, 25): 0.7, (25, 60): 1.0, (60, 100): 1.3, (100, 999): 1.5}
SEVERITY_COEF = {"轻度": 0.8, "中度": 1.0, "重度": 1.2}
_herb_cache = None
_ci_cache = None


def _load_safety():
    global _herb_cache, _ci_cache
    if _herb_cache is not None:
        return
    _herb_cache, _ci_cache = {}, set()
    try:
        conn = _db_conn()
    except Exception:
        return
    cur = conn.cursor()
    cur.execute("SELECT name, dosage_min, dosage_max, caution FROM herb")
    _herb_cache = {r[0]: {'min': float(r[1]), 'max': float(r[2]), 'caution': r[3]} for r in cur.fetchall()}
    cur.execute("SELECT herb_a, herb_b FROM herb_contraindication")
    for a, b in cur.fetchall():
        _ci_cache.add((a, b))
    conn.close()


def calc_dosage(base_g, weight, severity):
    wc = next((c for (lo, hi), c in WEIGHT_COEF.items() if lo <= weight < hi), 1.0)
    return round(base_g * wc * SEVERITY_COEF.get(severity, 1.0), 1)


def check_contraindications(herb_names):
    """十八反/十九畏查表（DB 不可用时返回空）"""
    _load_safety()
    if not _ci_cache:
        return []
    try:
        conn = _db_conn()
    except Exception:
        return []
    names = [n for n in herb_names if n]
    violations = []
    cur = conn.cursor()
    ids = {}
    for n in names:
        cur.execute("SELECT id FROM herb WHERE name=%s", (n,))
        row = cur.fetchone()
        ids[n] = row[0] if row else None
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = ids[names[i]], ids[names[j]]
            if a is None or b is None:
                continue
            if (a, b) in _ci_cache or (b, a) in _ci_cache:
                cur.execute("SELECT rule_type, description FROM herb_contraindication "
                            "WHERE (herb_a=%s AND herb_b=%s) OR (herb_a=%s AND herb_b=%s)", (a, b, b, a))
                rule = cur.fetchone()
                violations.append((names[i], names[j], rule[0] if rule else '禁忌'))
    conn.close()
    return violations


def safety_check(prescription):
    """分级校验：errors 硬拦截（禁忌/超上限8倍），warnings 软提示（人用区间/孕猪）"""
    _load_safety()
    herbs = prescription.get('herbs', [])
    errors, warnings = [], []
    errors += [f"{a}+{b}: {rule}" for a, b, rule in
               check_contraindications([h['name'] for h in herbs])]
    for h in herbs:
        info = _herb_cache.get(h['name'])
        if info and info['caution'] and '孕' in info['caution']:
            warnings.append(f"{h['name']}: {info['caution']}")
    for h in herbs:
        info = _herb_cache.get(h['name'])
        if not info:
            continue
        d = float(h.get('dosage_g', 0))
        if d > info['max'] * 8:
            errors.append(f"{h['name']}: 剂量{d}g 超区间上限{info['max']}g的8倍，疑似异常，需人工审核")
        elif d < info['min'] or d > info['max']:
            warnings.append(f"{h['name']}: {d}g 超出人用参考区间 {info['min']}-{info['max']}g（兽用整方给药请对照兽药典）")
    return {'safe': len(errors) == 0, 'errors': errors, 'warnings': warnings,
            'score': round(max(0.0, 1.0 - 0.3 * len(errors) - 0.05 * len(warnings)), 2)}


# ════════════════════════════════════════════════════════════
# 6. 论治主流水线
# ════════════════════════════════════════════════════════════
FULL_KB = True  # 小库全量注入（辨证库/论治库全量给 LLM，语义匹配更准）


def query_rewrite(disease, symptoms, temp, severity):
    """查询改写层：口语输入 → 标准检索词（失败返回 None，调用方用原始输入兜底）"""
    user = f"疾病：{disease}\n症状：{symptoms}\n体温：{temp}℃\n严重度：{severity}"
    try:
        return extract_json(call_qwen(QR_SYSTEM, user, temperature=0.0))
    except Exception:
        return None


def syndrome_stage(disease, symptoms, temp, weight, severity, q=None):
    """辨证Agent：知识注入（全量辨证库 + 典籍 Top5）+ SQL 检索 + 规则交叉验证 → LLM 辨证"""
    med_query = (q.get('classic_query') if q and q.get('classic_query')
                 else f"{disease} {symptoms} 辨证 治则")
    sym_docs = "\n".join(get_all('symptom_disease')) if FULL_KB else "\n".join(
        retrieve('symptom_disease', q.get('syndrome_query') if q else f"{disease} {symptoms} 体温{temp}", k=3))
    med_docs = "\n".join(retrieve('tcm_classics', med_query, k=5))

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
        cross_check = rule_cross_check(disease, temp, kw_llm + ' ' + ' '.join(kw_rule))
    except Exception:
        pass

    user = (f"辨病结果（参考，可能不准确）：{disease}\n临床症状：{symptoms}\n体温：{temp}℃\n"
            f"猪只信息：体重{weight}kg，{severity}病情\n"
            + (f"\nSQL精确检索候选（仅供参考，需与全量规则核对特异体征）：\n{sql_hits}" if sql_hits else "") +
            (f"\n规则交叉验证：{cross_check['reason']}" if cross_check and cross_check['checked'] else "") +
            "\n请辨证分型（以全量规则+特异体征为准，若与辨病结果矛盾必须指出）。")
    sx = extract_json(call_qwen(SX_SYSTEM.format(sym_docs=sym_docs, med_docs=med_docs),
                                user, temperature=0.0))
    sx['rule_cross_check'] = cross_check or {}
    if sx.get('disease_conflict') is None:
        sx['disease_conflict'] = {'upstream_disease': disease, 'evidence_disease': '',
                                  'conflict': False, 'reason': 'LLM未返回冲突检查'}
    return sx


def formula_stage(sx_result, pig_info):
    """组方Agent：全量论治库 + 典籍 Top5 → LLM 组方"""
    formula_docs = "\n".join(get_all('disease_formula')) if FULL_KB else "\n".join(
        retrieve('disease_formula', f"{sx_result.get('syndrome', '')} {sx_result.get('principle', '')} 组方", k=3))
    med_docs = "\n".join(retrieve('tcm_classics', "方剂 剂量 禁忌 加减", k=5))
    user = f"辨证结果：{json.dumps(sx_result, ensure_ascii=False)}\n猪只信息：{pig_info}\n请开具组方。"
    return extract_json(call_qwen(RX_SYSTEM.format(formula_docs=formula_docs, med_docs=med_docs),
                                  user, temperature=0.5))


def verify_stage(rx, weight, severity):
    """校验Agent（规则引擎）：灌服/煎汤类按体重换算，拌料类整方校验"""
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


def treatment_pipeline(disease, symptoms, temp, weight, severity, pig_extra=""):
    """辨病结果（label 或中文名）+ 临床症状 → 完整论治方案（辨证/组方/校验）

    disease: 辨病模型 label（app/influenza/prrs/mycoplasma/normal/other_disease），
             内部查 DB disease 表转中文名后再封装给 LLM；也兼容直接传中文名
    """
    disease = lookup_disease_name(disease)   # label → 中文病名（DB 查询）
    q = query_rewrite(disease, symptoms, temp, severity)
    sx = syndrome_stage(disease, symptoms, temp, weight, severity, q)
    rx = formula_stage(sx, f"体重{weight}kg，{severity}病情，{pig_extra}")
    report = verify_stage(rx, weight, severity)
    return {'syndrome': sx, 'prescription': rx, 'verification': report}


if __name__ == '__main__':
    result = treatment_pipeline(disease="猪支原体肺炎", symptoms="湿咳、痰多、呼吸粗，食欲下降",
                                temp=39.2, weight=70, severity="中度", pig_extra="4月龄育肥猪")
    print(json.dumps(result, ensure_ascii=False, indent=2))
