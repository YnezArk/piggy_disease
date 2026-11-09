# safety.py — 校验Agent：剂量计算 + 安全校验（确定性规则，非LLM）
# 数据权威源：MySQL pig_diag 的 herb 表（安全剂量区间）+ herb_contraindication 表（十八反/十九畏）
import pymysql
from config import DB

WEIGHT_COEF = {  # 体重系数（kg）
    (0, 25): 0.7, (25, 60): 1.0, (60, 100): 1.3, (100, 999): 1.5,
}
SEVERITY_COEF = {"轻度": 0.8, "中度": 1.0, "重度": 1.2}

_herb_cache = None   # {name: {dosage_min, dosage_max, caution}}
_herb_ids = None     # {name: id}
_ci_cache = None     # {(a,b): (rule_type, description)} 禁忌无序对（双向入表）


def _load():
    """一次性把药材区间、药材 id、配伍禁忌全部载入内存（后续校验零查库）。"""
    global _herb_cache, _herb_ids, _ci_cache
    if _herb_cache is not None:
        return
    conn = pymysql.connect(**DB)
    cur = conn.cursor()
    cur.execute("SELECT id, name, dosage_min, dosage_max, caution FROM herb")
    _herb_cache, _herb_ids = {}, {}
    for hid, name, lo, hi, cau in cur.fetchall():
        _herb_cache[name] = {'min': float(lo), 'max': float(hi), 'caution': cau}
        _herb_ids[name] = hid
    cur.execute("SELECT herb_a, herb_b, rule_type, description FROM herb_contraindication")
    _ci_cache = {}
    for a, b, rt, desc in cur.fetchall():
        _ci_cache[(a, b)] = (rt or '禁忌', desc or '')
        _ci_cache[(b, a)] = (rt or '禁忌', desc or '')
    conn.close()


def calc_dosage(base_g, weight, severity):
    """基础剂量 × 体重系数 × 病情系数（weight 越界时按 1.0 兜底，防 StopIteration）"""
    wc = next((c for (lo, hi), c in WEIGHT_COEF.items() if lo <= weight < hi), 1.0)
    sc = SEVERITY_COEF.get(severity, 1.0)
    return round(base_g * wc * sc, 1)


def check_contraindications(herb_names):
    """输入药材名列表 → 返回违规组合 [('甘草','甘遂','十八反'), ...]（内存比对）"""
    _load()
    names = [n for n in herb_names if n]
    violations = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = _herb_ids.get(names[i]), _herb_ids.get(names[j])
            if a is None or b is None:
                continue
            hit = _ci_cache.get((a, b))
            if hit:
                violations.append((names[i], names[j], hit[0]))
    return violations


def safety_check(prescription):
    """分级校验：
       errors（硬拦截）：十八反/禁忌、剂量超区间上限8倍（防LLM幻觉）
       warnings（软提示）：超人用参考区间、孕猪慎用药
       safe = 无 errors
    """
    _load()
    herbs = prescription.get('herbs', [])
    errors, warnings = [], []

    # 硬规则1：配伍禁忌（十八反/十九畏）
    errors += [f"{a}+{b}: {rule}" for a, b, rule in
               check_contraindications([h['name'] for h in herbs])]

    # 硬规则2：孕猪禁用/慎用
    for h in herbs:
        info = _herb_cache.get(h['name'])
        if info and info['caution'] and '孕' in info['caution']:
            warnings.append(f"{h['name']}: {info['caution']}")

    # 剂量：软提示（人用区间参考）+ 硬拦截（>8倍上限，明显幻觉）
    # 注：兽药典散剂整方配比可达人用上限5-6倍（如薄荷6g→30g），故阈值取8倍防误伤
    for h in herbs:
        info = _herb_cache.get(h['name'])
        if not info:
            continue
        d = float(h.get('dosage_g', 0))
        if d > info['max'] * 8:
            errors.append(f"{h['name']}: 剂量{d}g 超区间上限{info['max']}g的8倍，疑似异常，需人工审核")
        elif d < info['min'] or d > info['max']:
            warnings.append(f"{h['name']}: {d}g 超出人用参考区间 {info['min']}-{info['max']}g（兽用整方给药请对照兽药典）")

    return {
        'safe': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
        'score': round(max(0.0, 1.0 - 0.3 * len(errors) - 0.05 * len(warnings)), 2),
    }


if __name__ == '__main__':
    # 自测：故意植入禁忌和超标剂量
    test = {'herbs': [
        {'name': '甘草', 'dosage_g': 25.0},
        {'name': '甘遂', 'dosage_g': 2.0},   # 十八反：甘草反甘遂
        {'name': '麻黄', 'dosage_g': 80.0},  # 超标（上限15）
    ]}
    print(safety_check(test))
    print('剂量换算示例:', calc_dosage(30, 70, '中度'), 'g（黄芪30g × 育肥猪1.3 × 中度1.0）')
