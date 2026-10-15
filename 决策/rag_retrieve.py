# rag_retrieve.py — 本地内存 RAG 检索（零外部依赖，数据量小时最快最稳）
#
# 说明：ChromaDB 写入已验证，但其 hnswlib 在 Python 3.14 上查询会卡死；
#       本项目语料仅 253 片段，内存余弦检索毫秒级，足够使用。
#       retrieve(name, query, k) 接口与 ChromaDB 版兼容，可无缝替换。
#
# 用法：
#   from rag_retrieve import retrieve
#   docs = retrieve('symptom_disease', '体温39.2 湿咳 痰多', k=3)

import csv, os, hashlib, math
import jieba

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
    """构建内存索引：辨证库/论治库来自 CSV，典籍库来自 classics/*.txt"""
    global _DB
    _DB = {'symptom_disease': [], 'disease_formula': [], 'tcm_classics': []}

    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    # ① 辨证库
    p = os.path.join(base, 'kg', 'symptom_disease.csv')
    if os.path.exists(p):
        with open(p, encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                doc = (f"体温{row['temperature_min'] or '不限'}~{row['temperature_max'] or '不限'}℃，"
                       f"咳喘：{row['cough_type']}，排泄物：{row['excretion']}，其他体征：{row['other_signs']} → "
                       f"证候：{row['syndrome']}，疾病：{row['disease'] or '无'}，鉴别依据：{row['evidence']}")
                _DB['symptom_disease'].append((doc, '辨证库', _embed(doc)))
    # ② 论治库
    p = os.path.join(base, 'kg', 'disease_formula.csv')
    if os.path.exists(p):
        with open(p, encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                doc = (f"证候/疾病：{row['disease']} → 基础方剂：{row['base_formula']}，"
                       f"组成：{row['herbs']}，加减：{row['add_rule']}，用法：{row['usage']}，"
                       f"疗程：{row['course']}，禁忌：{row['contraindication']}，出处：{row['reference']}")
                _DB['disease_formula'].append((doc, '论治库', _embed(doc)))
    # ③ 典籍库
    for root, _, files in os.walk(os.path.join(base, 'rag', 'classics')):
        for fn in files:
            if not fn.endswith(('.txt', '.md')):
                continue
            path = os.path.join(root, fn)
            # 展示用来源：友好名称（审计时可按文件名在 data/rag/classics/ 下定位原文件）
            friendly = f"典籍·{fn.replace('.txt', '').replace('.md', '')}"
            with open(path, encoding='utf-8') as fh:
                text = fh.read()
            for chunk in [p.strip() for p in text.split('\n') if len(p.strip()) > 30]:
                _DB['tcm_classics'].append((chunk, friendly, _embed(chunk)))

def retrieve(name, query, k=3):
    """按余弦相似度返回 Top-K 片段，格式：['【来源：X】内容', ...]"""
    if _DB is None:
        _load()
    if name not in _DB:
        raise ValueError(f'未知知识库: {name}，可选: {list(_DB.keys())}')
    qv = _embed(query)
    scored = sorted(
        ((_cos(doc_vec, qv), doc, src) for doc, src, doc_vec in _DB[name]),
        key=lambda x: -x[0],
    )
    return [f"【来源：{src}】{doc}" for score, doc, src in scored[:k] if score > 0]

def get_all(name):
    """返回某库全部条目（全量注入用，带【来源】标签）。
       小库（辨证库9条/论治库14条）全量仅约3.5k token，可全量给LLM做全局判断"""
    if _DB is None:
        _load()
    if name not in _DB:
        raise ValueError(f'未知知识库: {name}，可选: {list(_DB.keys())}')
    return [f"【来源：{src}】{doc}" for doc, src, _ in _DB[name]]


def stats():
    if _DB is None:
        _load()
    return {name: len(items) for name, items in _DB.items()}

if __name__ == '__main__':
    print('库容量:', stats())
    for q, name in [
        ('体温39.2 湿咳 痰多 呼吸粗', 'symptom_disease'),
        ('疫热壅肺 清热化痰 组方', 'disease_formula'),
        ('支原体肺炎 干咳 治疗 中药', 'tcm_classics'),
    ]:
        print(f'\n=== {name} 查询: {q} ===')
        for d in retrieve(name, q, k=3):
            print(' ', d[:110])
