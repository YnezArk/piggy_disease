# interactive_demo.py — 诊疗决策交互式手动测试终端
#
# 用法: python interactive_demo.py
# 逐项输入（回车=使用示例默认值），输出完整诊疗报告（辨证+组方+校验+引用）
# 测完一个案例后自动询问是否继续（输入 q / Ctrl+C 退出）
#
# 运行示例（全回车即可复现）:
#   python interactive_demo.py
#   → 疾病: 猪支原体肺炎 | 症状: 湿咳、痰多、呼吸粗、食欲下降
#   → 体温: 39.2 | 体重: 70 | 严重度: 中度
#   → 输出: 疫热壅肺 → 清肺散（板蓝根30君...）→ 校验通过

import sys

DISEASES = ["猪支原体肺炎", "猪流感", "猪肺疫", "猪传染性胸膜肺炎", "混合感染"]


def ask(prompt, default=""):
    """带默认值提示，回车用默认"""
    if default:
        s = input(f"{prompt} [{default}]: ").strip()
    else:
        s = input(f"{prompt}: ").strip()
    return s or default


def ask_float(prompt, default):
    """数值输入，非法输入回退默认值"""
    s = ask(prompt, str(default))
    try:
        return float(s)
    except ValueError:
        print(f"  ⚠️ 输入'{s}'非数字，使用默认值 {default}")
        return default


def pick_disease():
    print("\n可选疾病:")
    for i, d in enumerate(DISEASES, 1):
        print(f"  {i}. {d}")
    s = input("选择编号(1-5)或直接输入疾病名 [1]: ").strip()
    if s.isdigit() and 1 <= int(s) <= len(DISEASES):
        return DISEASES[int(s) - 1]
    return s or DISEASES[0]


def run_once(no):
    print(f"\n{'='*56}")
    print(f"  案例 {no} —— 请输入诊疗信息（回车=示例默认值）")
    print(f"{'='*56}")

    disease = pick_disease()
    symptoms = ask("临床症状(越具体辨证越准)", "湿咳、痰多、呼吸粗、食欲下降")
    temp = ask_float("体温(℃)", 39.2)
    weight = ask_float("体重(kg)", 70)
    severity = ask("严重度(轻度/中度/重度)", "中度")
    pig_house = ask("猪舍编号(可空)", "")
    extra = ask("补充信息(月龄等，可空)", "4月龄育肥猪")

    from therapy_engine import treatment_pipeline
    print("\n[调用论治引擎中...]")
    try:
        r = treatment_pipeline(
            disease=disease, symptoms=symptoms,
            temp=temp, weight=weight, severity=severity,
            pig_extra=extra or f"{weight}kg猪")
    except Exception as e:
        print(f"\n❌ 运行失败: {e}")
        return False

    # ── 输出诊疗报告 ──
    sx, rx, vf = r['syndrome'], r['prescription'], r['verification']
    print(f"\n{'='*56}")
    print("  诊疗报告")
    print(f"{'='*56}")
    if pig_house:
        print(f"猪舍: {pig_house}")
    print(f"【辨证】{sx.get('stage', '')} · {sx.get('syndrome', '')}")
    print(f"  治则: {sx.get('principle', '')}")
    print("  依据: " + "; ".join(sx.get('evidence', [])))
    # 辨病-辨证对照（证据指向疾病 + 规则交叉验证）
    dc = sx.get('disease_conflict', {})
    if dc:
        flag = "⚠️ 不一致" if dc.get('conflict') else "一致"
        print(f"  疾病对照: 上游辨病[{dc.get('upstream_disease', '?')}] vs "
              f"证据指向[{dc.get('evidence_disease', '?')}] —— {flag}")
        if dc.get('conflict'):
            print(f"    ↳ 说明: {dc.get('reason', '')[:120]}")
    rc = sx.get('rule_cross_check') or {}
    if rc and rc.get('checked'):
        hits = rc.get('hits', [])
        hit_desc = "; ".join(f"{h.get('syndrome', '?')}→{h.get('disease', '?')}"
                             for h in hits[:3]) or "无命中"
        flag = "⚠️ 矛盾，建议核实辨病" if rc.get('conflict') else "一致"
        print(f"  规则核验: 命中[{hit_desc}] vs 上游[{rc.get('upstream_disease', '?')}] —— {flag}")
        print(f"    ↳ {rc.get('reason', '')}")
    print(f"\n【组方】{rx.get('base_formula', '')}")
    print(f"  {'药名':<8}{'剂量(g)':<10}{'君臣佐使'}")
    print(f"  {'-'*28}")
    for h in rx.get('herbs', []):
        print(f"  {h['name']:<8}{h['dosage_g']:<10}{h.get('role', '')}")
    if rx.get('add_notes'):
        print(f"  加减说明: {'; '.join(rx['add_notes'])}")
    print(f"  用法: {rx.get('preparation', '')} | 疗程: {rx.get('course', '')}")
    if rx.get('contraindications'):
        print(f"  禁忌: {'; '.join(rx['contraindications'])}")
    print(f"\n【安全校验】{'✅ 通过' if vf['safe'] else '❌ 拦截'}")
    for e in vf.get('errors', []):
        print(f"  [拦截] {e}")
    for w in vf.get('warnings', []):
        print(f"  [提示] {w}")
    print("\n【引用来源】")
    for ref in rx.get('references', []):
        print(f"  · {ref[:100]}")
    print("\n  ⚠️ 本结果由AI辅助生成，仅供兽医参考，用药请遵兽医指导")
    return True


def main():
    print("=" * 56)
    print("  猪咳嗽诊疗决策板块 · 交互式手动测试终端")
    print("  回车使用示例默认值 | 随时 Ctrl+C 退出")
    print("=" * 56)
    no = 1
    while True:
        try:
            run_once(no)
            no += 1
            again = input("\n继续测试下一个案例? (回车=继续, q=退出): ").strip()
            if again.lower() in ("q", "quit", "exit"):
                break
        except (KeyboardInterrupt, EOFError):
            print("\n已退出。")
            break
    print("测试结束。")


if __name__ == '__main__':
    sys.exit(main())
