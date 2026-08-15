# interactive_audio_demo.py — 辨病模块交互式音频测试终端
#
# 用法: python interactive_audio_demo.py
# 流程: 选择样本组（5 类标注 + unknown + 自定义路径）→ 选文件 → 输出辨病报告
# 测完一个自动询问是否继续（q / Ctrl+C 退出）
#
# 运行示例:
#   python interactive_audio_demo.py
#   → 选择组: 1 (normal)
#   → 选择文件: 5
#   → 输出: normal 健康猪只 0.98 | 概率分布 | 与真实标签对照

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_ROOT = os.path.join(BASE_DIR, "pig_cough_data")
GROUPS = ["normal", "influenza", "prrs", "mycoplasma", "app", "unknown"]
DISEASE_NAMES = ["健康猪只", "猪流行性感冒", "猪蓝耳病", "猪支原体肺炎", "猪传染性胸膜肺炎"]
LABEL_NAMES = ["normal", "influenza", "prrs", "mycoplasma", "app"]


def list_samples():
    """{组名: [(序号, 文件名), ...]}，全量按组归档。"""
    out = {}
    for g in GROUPS:
        folder = os.path.join(AUDIO_ROOT, g)
        if os.path.isdir(folder):
            out[g] = [(i, f) for i, f in enumerate(
                sorted(x for x in os.listdir(folder) if x.lower().endswith(".wav")), 1)]
    return out


def show_groups(samples):
    print("\n可选样本组:")
    for i, g in enumerate(GROUPS, 1):
        n = len(samples.get(g, []))
        truth = DISEASE_NAMES[LABEL_NAMES.index(g)] if g in LABEL_NAMES else "未标注"
        print(f"  {i}. {g:12s}  {n:3d} 个文件  ({truth})")
    print("  7. 输入自定义 wav 路径")


def show_files(g, files):
    print(f"\n【{g}】共 {len(files)} 个文件:")
    for idx, fn in files:
        print(f"  {idx:3d}. {fn}")


def print_report(r, truth=None):
    print(f"\n{'='*56}")
    print(f"  辨病报告")
    print(f"{'='*56}")
    mark = "✅" if truth and truth == r["label"] else ("❌" if truth else "·")
    print(f"【结果】{mark} {r['disease']}  (label={r['label']})")
    if truth:
        print(f"  真实标签: {truth}  {'一致' if truth == r['label'] else '不一致'}")
    else:
        print(f"  真实标签: 未知（未标注样本）")
    print(f"  置信度: {r['confidence']:.4f}")
    print(f"  症状模板: {r['symptoms']}")

    print("\n  概率分布:")
    for i, t in enumerate(r["top3"]):
        bar = "█" * max(1, int(t["confidence"] * 30))
        print(f"    {t['label']:12s} {bar:30s} {t['confidence']:.4f}  {t['disease']}")
    print("\n  ⚠️ 本结果由AI辅助生成，仅供兽医参考，最终诊断请结合临床")


def main():
    from predict import diagnose, load_model
    samples = list_samples()
    total = sum(len(v) for v in samples.values())
    print("=" * 56)
    print("  辨病模块 · 交互式音频测试终端")
    print(f"  样本库: {total} 个 wav（5 类标注 + unknown）| q 退出 | Ctrl+C 退出")
    print("=" * 56)

    # 模型选择
    ms = input("\n模型 (1=SSLRB[推荐] 2=SVM Baseline) [1]: ").strip()
    model_name = "sslr" if ms != "2" else "svm"
    try:
        model = load_model(model_name)
    except FileNotFoundError as e:
        print(f"❌ {e}")
        return 1
    print(f"已加载: {model_name}")

    while True:
        try:
            show_groups(samples)
            s = input("\n选择组(1-7)或输入 wav 路径，q 退出: ").strip()
            if s.lower() in ("q", "quit", "exit"):
                break
            wav_path = None
            truth = None

            if s.isdigit() and 1 <= int(s) <= 7:
                gi = int(s) - 1
                if gi < 6:
                    g = GROUPS[gi]
                    files = samples.get(g, [])
                    if not files:
                        print(f"⚠️ 组 {g} 无文件")
                        continue
                    show_files(g, files)
                    f = input(f"选择文件编号(1-{len(files)})，或输入文件名: ").strip()
                    if f.isdigit() and 1 <= int(f) <= len(files):
                        fn = files[int(f) - 1][1]
                    elif f and f.lower().endswith(".wav"):
                        fn = f
                    else:
                        print("⚠️ 无效选择")
                        continue
                    wav_path = os.path.join(AUDIO_ROOT, g, fn)
                    truth = g if g in LABEL_NAMES else None
                else:
                    wav_path = input("输入 wav 完整路径: ").strip()
            elif s.lower().endswith(".wav") and os.path.exists(s):
                wav_path = s
            else:
                print("⚠️ 无效输入")
                continue

            if not wav_path or not os.path.exists(wav_path):
                print(f"❌ 文件不存在: {wav_path}")
                continue

            print(f"\n[正在分析: {os.path.basename(wav_path)} ...]")
            r = diagnose(wav_path, model=model, model_name=model_name)
            print_report(r, truth)

            again = input("\n继续测试? (回车=继续, q=退出): ").strip()
            if again.lower() in ("q", "quit", "exit"):
                break
        except (KeyboardInterrupt, EOFError):
            print("\n已退出。")
            break
    print("测试结束。")


if __name__ == "__main__":
    sys.exit(main())
