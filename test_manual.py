# test_manual.py — 诊疗决策板块手动测试脚本
#
# 用法（三选一）：
#   python test_manual.py            # 交互菜单，选块运行
#   python test_manual.py all        # 全部测试（API块需服务已启动）
#   python test_manual.py env|rag|safety|cases|api|sql   # 只跑某块
#
# 每项输出 [PASS]/[FAIL] + 详情，末尾汇总。测试样例见《诊疗决策板块_测试手册.md》

import json
import os
import sys
import urllib.request

from dotenv import load_dotenv
load_dotenv()
from config import DB

PASS, FAIL = 0, 0
RESULTS = []


def t(name, ok, detail=""):
    """记录一条测试结果"""
    global PASS, FAIL
    if ok:
        PASS += 1
    else:
        FAIL += 1
    RESULTS.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" | {detail}" if detail else ""))


# ══════════════════ 1. 环境检查 ══════════════════
def test_env():
    print("\n========== 1. 环境检查 ==========")
    ok_key = bool(os.environ.get("DASHSCOPE_API_KEY", ""))
    t("DASHSCOPE_API_KEY 已配置(.env)", ok_key, "" if ok_key else "检查 .env 文件")
    try:
        import pymysql
        conn = pymysql.connect(**DB)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM herb")
        herb_n = cur.fetchone()[0]
        conn.close()
        t("MySQL 连接 + pig_diag 库可读", herb_n > 0, f"herb 表 {herb_n} 味药")
    except Exception as e:
        t("MySQL 连接 + pig_diag 库可读", False, str(e))
    try:
        from rag_retrieve import stats
        s = stats()
        t("rag_retrieve 内存索引构建", sum(s.values()) > 0, str(s))
    except Exception as e:
        t("rag_retrieve 内存索引构建", False, str(e))


# ══════════════════ 2. RAG 检索质量 ══════════════════
def test_rag():
    print("\n========== 2. RAG 三库检索质量 ==========")
    from rag_retrieve import retrieve

    def check(name, query, expect_kw, k=3):
        docs = retrieve(name, query, k=k)
        hit = any(expect_kw in d for d in docs)
        t(f"检索[{name}] {query[:20]}... → 命中'{expect_kw}'", hit,
          docs[0][:80] if docs else "无结果")
        return docs

    check('symptom_disease', '体温39.2 湿咳 痰多 呼吸粗', '疫热壅肺')
    check('symptom_disease', '高热40.5 干咳 突发 群发', '邪袭肺卫')
    check('disease_formula', '疫热壅肺 清热化痰 组方', '清肺散')
    check('disease_formula', '邪袭肺卫 风热 解表', '银翘散')
    check('tcm_classics', '支原体肺炎 干咳 治疗', '支原体肺炎')
    check('tcm_classics', '气阴两伤 生脉散 益气养阴', '气阴两伤')


# ══════════════════ 3. 安全校验 ══════════════════
def test_safety():
    print("\n========== 3. 安全校验（safety.py） ==========")
    from safety import safety_check, calc_dosage

    # 3.1 正常方剂 → 通过
    r = safety_check({'herbs': [{'name': '黄芪', 'dosage_g': 30},
                                {'name': '茯苓', 'dosage_g': 15},
                                {'name': '甘草', 'dosage_g': 10}]})
    t("正常组方 → 校验通过", r['safe'] and not r['errors'],
      f"score={r['score']}, warnings={len(r['warnings'])}")

    # 3.2 十八反 → 拦截
    r = safety_check({'herbs': [{'name': '甘草', 'dosage_g': 10},
                                {'name': '甘遂', 'dosage_g': 2}]})
    t("十八反(甘草+甘遂) → 拦截", not r['safe'] and any('甘遂' in e for e in r['errors']),
      str(r['errors']))

    # 3.3 幻觉剂量 → 拦截
    r = safety_check({'herbs': [{'name': '麻黄', 'dosage_g': 500}]})
    t("幻觉剂量(麻黄500g) → 拦截", not r['safe'] and any('麻黄' in e for e in r['errors']),
      str(r['errors']))

    # 3.4 孕猪慎用 → 软提示
    r = safety_check({'herbs': [{'name': '麻黄', 'dosage_g': 8}]})
    t("孕猪慎用药(麻黄) → 软提示", r['safe'] and any('孕' in w for w in r['warnings']),
      str(r['warnings']))

    # 3.5 剂量换算
    d = calc_dosage(30, 70, '中度')
    t("剂量换算(30g×育肥猪1.3×中度1.0)", abs(d - 39.0) < 0.1, f"={d}g")


# ══════════════════ 4. 论治引擎端到端（LLM） ══════════════════
CASES = [
    {
        "no": "A", "desc": "支原体肺炎·中期·湿咳",
        "disease": "猪支原体肺炎", "symptoms": "湿咳、痰多、呼吸粗、食欲下降",
        "temp_c": 39.2, "weight_kg": 70, "severity": "中度",
        "expect_syndrome": "疫热壅肺",
    },
    {
        "no": "B", "desc": "猪流感·前期·干咳高热",
        "disease": "猪流感", "symptoms": "干咳、鼻流清涕、突发高热、精神萎靡",
        "temp_c": 40.5, "weight_kg": 50, "severity": "轻度",
        "expect_syndrome": "邪袭肺卫",
    },
    {
        "no": "C", "desc": "猪肺疫·中期·呼吸困难",
        "disease": "猪肺疫", "symptoms": "咳嗽、呼吸困难、颈部肿胀、便秘",
        "temp_c": 40.8, "weight_kg": 80, "severity": "重度",
        "expect_syndrome": "疫热壅肺",
    },
    {
        "no": "D", "desc": "混合感染·后期·气阴两伤",
        "disease": "混合感染", "symptoms": "咳嗽喘促、精神萎靡、病程长、反复发作",
        "temp_c": 38.5, "weight_kg": 60, "severity": "重度",
        "expect_syndrome": "气阴两伤",
    },
    {
        "no": "E", "desc": "★辨病纠错：上游错判支原体，症状实为流感",
        "disease": "猪支原体肺炎",   # 故意错误的上游辨病结果
        "symptoms": "突发高热40.5℃、干咳阵咳、鼻流清涕、全群爆发",
        "temp_c": 40.5, "weight_kg": 50, "severity": "轻度",
        "expect_syndrome": "邪袭肺卫",   # 按症状独立辨证，不被锚定
        "expect_conflict": True,          # 必须指出与上游辨病矛盾
    },
]


def test_cases(only=None):
    print("\n========== 4. 论治引擎端到端（调用 qwen3.7-flash） ==========")
    from therapy_engine import treatment_pipeline

    cases = [c for c in CASES if only is None or c["no"] == only]
    for c in cases:
        print(f"\n--- 案例{c['no']}：{c['desc']} ---")
        try:
            r = treatment_pipeline(
                disease=c["disease"], symptoms=c["symptoms"],
                temp=c["temp_c"], weight=c["weight_kg"], severity=c["severity"],
                pig_extra=f"{c['weight_kg']}kg猪")
            got = r['syndrome'].get('syndrome', '')
            ok_syndrome = c["expect_syndrome"] in got or got in c["expect_syndrome"]
            t(f"案例{c['no']} 辨证 → {got}（预期含'{c['expect_syndrome']}'）", ok_syndrome)
            t(f"案例{c['no']} 组方非空 + 引用来源", bool(r['prescription'].get('herbs'))
              and bool(r['prescription'].get('references')),
              f"基础方: {r['prescription'].get('base_formula')}")
            t(f"案例{c['no']} 校验通过（无硬拦截）", r['verification']['safe'],
              f"errors={r['verification']['errors']}, warnings={len(r['verification']['warnings'])}")
            # 案例E 额外验证：辨病纠错机制
            if c.get("expect_conflict"):
                dc = r['syndrome'].get('disease_conflict') or {}
                rc = r['syndrome'].get('rule_cross_check') or {}
                t("案例E 规则交叉验证 → 检测到矛盾",
                  rc.get('conflict') is True, rc.get('reason', '')[:80])
                t("案例E LLM冲突检查 → conflict=true + 给出证据方向",
                  dc.get('conflict') is True and dc.get('evidence_disease', '') != '',
                  f"证据指向: {dc.get('evidence_disease', '')}")
        except Exception as e:
            t(f"案例{c['no']} 运行", False, str(e)[:120])


# ══════════════════ 5. API 服务 ══════════════════
def test_api():
    print("\n========== 5. API 服务（需已启动 uvicorn） ==========")
    BASE = "http://127.0.0.1:8000"
    # 检查服务
    try:
        with urllib.request.urlopen(f"{BASE}/api/health", timeout=5) as resp:
            t("GET /api/health", json.loads(resp.read())["status"] == "ok")
    except Exception as e:
        t("GET /api/health", False, f"服务未启动？运行: python -m uvicorn api_server:app --port 8000 ({e})")
        return

    payload = {
        "disease": "猪支原体肺炎", "confidence": 0.91,
        "symptoms": "湿咳、痰多、呼吸粗、食欲下降",
        "temp_c": 39.2, "weight_kg": 70, "severity": "中度",
        "pig_house": "测试舍-1", "pig_extra": "4月龄",
    }
    try:
        req = urllib.request.Request(f"{BASE}/api/diagnosis",
                                     data=json.dumps(payload).encode('utf-8'),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=180) as resp:
            r = json.loads(resp.read().decode('utf-8'))
        t("POST /api/diagnosis 返回 code=0", r.get("code") == 0,
          f"trace_id={r.get('trace_id')}")
        if r.get("code") == 0:
            t("响应含 证型/组方/校验 三件套",
              all(k in r for k in ("syndrome", "prescription", "verification")))
            # 验证落库
            import pymysql
            conn = pymysql.connect(**DB)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM prescription_record WHERE diagnosis_id IN "
                        "(SELECT id FROM diagnosis_record WHERE pig_house='测试舍-1')")
            n = cur.fetchone()[0]
            conn.close()
            t("落库成功（diagnosis_record + prescription_record）", n >= 1, f"处方记录 {n} 条")
    except Exception as e:
        t("POST /api/diagnosis", False, str(e)[:150])


# ══════════════════ 6. 数据库查询（Text-to-SQL 参照） ══════════════════
def test_sql():
    print("\n========== 6. 数据库查询验证 ==========")
    import pymysql
    conn = pymysql.connect(**DB)
    cur = conn.cursor()

    # 6.1 辨证库：按体征查证候
    cur.execute('''SELECT s.name FROM syndrome_mapping m JOIN syndrome s ON s.id = m.syndrome_id
      WHERE (m.temperature_min IS NULL OR 39.2 >= m.temperature_min)
        AND (m.temperature_max IS NULL OR 39.2 <= m.temperature_max)
        AND m.cough_type LIKE '%湿咳%' ORDER BY m.weight DESC LIMIT 1''')
    row = cur.fetchone()
    t("SQL辨证查询(39.2℃+湿咳) → 疫热壅肺", row and row[0] == '疫热壅肺', str(row))

    # 6.2 论治库：证候→方剂+组成
    cur.execute('''SELECT f.name, COUNT(fh.herb_id) FROM formula f
      JOIN formula_herb fh ON fh.formula_id = f.id WHERE f.syndrome_id = 2 GROUP BY f.id''')
    rows = cur.fetchall()
    t("SQL组方查询(疫热壅肺) → 有方剂", len(rows) >= 2, f"{len(rows)} 首方")

    # 6.3 禁忌校验 SQL
    cur.execute('''SELECT COUNT(*) FROM herb_contraindication''')
    n = cur.fetchone()[0]
    t("配伍禁忌表非空", n >= 6, f"{n} 条")

    # 6.4 知识来源完整性（防幻觉审计）
    cur.execute('''SELECT COUNT(*) FROM herb WHERE reference_id IS NOT NULL''')
    n_h = cur.fetchone()[0]
    cur.execute('''SELECT COUNT(*) FROM formula WHERE reference_id IS NOT NULL''')
    n_f = cur.fetchone()[0]
    t("药材/方剂引用来源完整", n_h >= 40 and n_f >= 10, f"herb {n_h}/{48} 方剂 {n_f}/{14} 有出处")
    conn.close()


# ══════════════════ 主入口 ══════════════════
BLOCKS = {
    "env": ("环境检查", test_env),
    "rag": ("RAG检索质量", test_rag),
    "safety": ("安全校验", test_safety),
    "cases": ("论治引擎端到端", test_cases),
    "api": ("API服务", test_api),
    "sql": ("数据库查询", test_sql),
}


def main():
    arg = sys.argv[1].lower() if len(sys.argv) > 1 else None
    if arg == "all" or arg is None and not sys.stdin.isatty():
        for _, fn in BLOCKS.values():
            fn()
    elif arg in BLOCKS:
        BLOCKS[arg][1]()
    else:
        print("诊疗决策板块测试脚本")
        print("用法: python test_manual.py [all|" + "|".join(BLOCKS) + "]")
        print("\n交互菜单:")
        items = list(BLOCKS.items()) + [("all", ("全部测试", None))]
        for i, (k, (name, _)) in enumerate(items, 1):
            print(f"  {i}. {name} ({k})")
        choice = input("\n选择(1-7，回车=全部): ").strip()
        if choice:
            try:
                idx = int(choice) - 1
            except ValueError:
                idx = -1
            if 0 <= idx < len(items):
                items[idx][1][1]()
            else:
                print("无效选择，跳过。")

    print(f"\n{'='*40}\n结果汇总: {PASS} 通过 / {FAIL} 失败")
    if FAIL:
        print("失败项:")
        for name, ok, detail in RESULTS:
            if not ok:
                print(f"  - {name}: {detail}")
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
