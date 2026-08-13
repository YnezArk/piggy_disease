# kb_lookup.py — 确定性知识检索与规则交叉验证（非LLM）
# 依赖: MySQL pig_diag（syndrome_mapping/syndrome/disease 表），配置见 config.py
# 职责：① 体征词同义词归一 + 规则提取 ② Text-to-SQL 精确查辨证库 ③ 规则交叉验证
import re

import pymysql

from config import DB

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


_disease_aliases = None  # {name: set(别名展开)}，别名归一缓存


def _load_disease_aliases():
    """从 MySQL disease 表加载 病名+别名 → 归一集合（供交叉验证比较）"""
    global _disease_aliases
    if _disease_aliases is not None:
        return
    conn = pymysql.connect(**DB)
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
    """别名归一比较：'猪蓝耳病' vs '猪繁殖与呼吸综合征' → True（同一疾病）"""
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
    """确定性交叉验证（非LLM）：全部命中规则逐一对比映射疾病与上游辨病（别名归一）。
       conflict=true 仅当【没有任何】命中规则与上游同病（上游辨病可能错误）；
       存在同病规则时弱化为"多病可能"提示（混合感染/症状交叉），不判上游错误"""
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
    return {
        "checked": True,
        "hits": [{"syndrome": r[0], "disease": r[1] or "未标注", "weight": r[3]}
                 for r in rows],
        "upstream_disease": disease,
        "conflict": len(same) == 0,
        "reason": reason,
    }
