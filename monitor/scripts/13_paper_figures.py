# -*- coding: utf-8 -*-
"""
13_paper_figures.py —— 一键生成答辩用关键图片（复现论文搭建流程的可视化证据）
输出目录: results/paper_figures/    运行: python scripts\13_paper_figures.py
"""
import sys, io, glob, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

import config
from src.audio_io import load_audio
from src.preprocess import bandpass_filter, pre_emphasis, frame_signal, energy_endpoint_detect
from src.features import extract_mfcc, add_deltas

OUT = config.RESULT_DIR / "paper_figures"
OUT.mkdir(parents=True, exist_ok=True)
SR = config.SAMPLE_RATE


def pick(patterns):
    for pat in patterns:
        hits = sorted(glob.glob(str(config.RAW_DIR / pat)))
        if hits:
            return hits[0]
    return None


cough_path = pick(["cough/app_a.wav", "cough/flu_a.wav", "cough/app_*_v.wav", "cough/*.wav"])
noncough_path = pick(["non_cough/gander_1.wav", "non_cough/norm_oink_1.wav", "non_cough/norm_*.wav", "non_cough/*.wav"])
print("咳嗽样本:", cough_path); print("非咳嗽样本:", noncough_path)

y_raw, sr = load_audio(cough_path)
yb = bandpass_filter(y_raw, sr=sr)
yp = pre_emphasis(yb)

# ---------- 图1：预处理前后波形对比 ----------
t = np.arange(len(y_raw)) / sr
fig, ax = plt.subplots(3, 1, figsize=(11, 7), sharex=True)
ax[0].plot(t, y_raw, lw=0.7, color="#4C72B0"); ax[0].set_title("(a) 原始采集波形")
ax[1].plot(t, yb, lw=0.7, color="#55A868"); ax[1].set_title("(b) 四阶巴特沃斯带通滤波后（100~2000 Hz）")
ax[2].plot(t, yp, lw=0.7, color="#C44E52"); ax[2].set_title("(c) 预加重后（α=0.97，高频相对增强）")
for a in ax: a.set_ylabel("幅度"); a.grid(alpha=0.3)
ax[2].set_xlabel("时间 / s")
plt.tight_layout(); fig.savefig(OUT / "fig1_预处理前后波形对比.png", dpi=200, bbox_inches="tight"); plt.close(fig)
print("已生成 fig1")

# ---------- 图2：端点检测 ----------
frames = frame_signal(yp, config.WIN_LENGTH, config.HOP_LENGTH)
energy = np.sqrt((frames ** 2).mean(axis=1))
te = energy.mean() + config.STE_THRESH_COEF * energy.std()
segs = energy_endpoint_detect(yp, sr=sr)
fig, ax = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
ax[0].plot(t, yp, lw=0.6, color="#4C72B0")
for s, e in segs: ax[0].axvspan(s / sr, e / sr, color="orange", alpha=0.35)
ax[0].set_title("(a) 预加重波形 + 端点检测出的有效语音段（橙色）"); ax[0].set_ylabel("幅度"); ax[0].grid(alpha=0.3)
te_t = (np.arange(len(energy)) * config.HOP_LENGTH + config.WIN_LENGTH / 2) / sr
ax[1].plot(te_t, energy, lw=1.0, color="#55A868", label="帧 RMS 短时能量 E(n)")
ax[1].axhline(te, color="#C44E52", ls="--", lw=1.5, label=f"自适应阈值 TE=μ+0.5σ={te:.4f}")
ax[1].fill_between(te_t, 0, energy, where=energy > te, color="orange", alpha=0.35)
ax[1].set_title("(b) 短时能量与自适应阈值（高于阈值的帧判为有效）")
ax[1].set_xlabel("时间 / s"); ax[1].set_ylabel("RMS 能量"); ax[1].legend(); ax[1].grid(alpha=0.3)
plt.tight_layout(); fig.savefig(OUT / "fig2_端点检测.png", dpi=200, bbox_inches="tight"); plt.close(fig)
print("已生成 fig2（检出段数 %d）" % len(segs))

# ---------- 图3：MFCC 对比 ----------
y2, _ = load_audio(noncough_path) if noncough_path else (yp, sr)
f_cough = extract_mfcc(yp, sr=sr).T
f_non = extract_mfcc(pre_emphasis(bandpass_filter(y2, sr=sr)) if noncough_path else yp, sr=sr).T
fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
im0 = ax[0].imshow(f_cough, aspect="auto", origin="lower", cmap="viridis")
ax[0].set_title("(a) 咳嗽声 MFCC 特征图"); ax[0].set_xlabel("帧"); ax[0].set_ylabel("MFCC 维数"); plt.colorbar(im0, ax=ax[0])
im1 = ax[1].imshow(f_non, aspect="auto", origin="lower", cmap="viridis")
ax[1].set_title("(b) 非咳嗽声 MFCC 特征图"); ax[1].set_xlabel("帧"); ax[1].set_ylabel("MFCC 维数"); plt.colorbar(im1, ax=ax[1])
plt.tight_layout(); fig.savefig(OUT / "fig3_MFCC特征对比.png", dpi=200, bbox_inches="tight"); plt.close(fig)
print("已生成 fig3")

# ---------- 图4：39 维特征 ----------
feat39 = add_deltas(extract_mfcc(yp, sr=sr))
fig, ax = plt.subplots(figsize=(11, 4.2))
im = ax.imshow(feat39.T, aspect="auto", origin="lower", cmap="magma")
ax.set_title("MFCC(13) + 一阶差分(13) + 二阶差分(13) = 39 维特征矩阵")
ax.set_xlabel("帧（10 ms/帧）"); ax.set_ylabel("39 维特征")
ax.axhline(12.5, color="w", ls="--", lw=1); ax.axhline(25.5, color="w", ls="--", lw=1)
ax.text(2, 6, "MFCC 1-13", color="w", fontsize=9)
ax.text(2, 19, "一阶差分 14-26", color="w", fontsize=9)
ax.text(2, 32, "二阶差分 27-39", color="w", fontsize=9)
plt.colorbar(im, ax=ax); plt.tight_layout(); fig.savefig(OUT / "fig4_39维特征.png", dpi=200, bbox_inches="tight"); plt.close(fig)
print("已生成 fig4")

# ---------- 图5：数据集类别分布（按 data/raw 真实类别统计） ----------
KEY = [("app", "胸膜肺炎", 0), ("myco", "支原体", 0), ("prrs", "蓝耳病", 0),
       ("flu", "猪流感", 0), ("rhino", "鼻炎", 0), ("gander", "鹅鸣", 1),
       ("oink", "哼哼", 1), ("scream", "尖叫", 1), ("snore", "呼噜", 1),
       ("hungry", "饥饿", 1), ("play", "玩耍", 1), ("environment", "环境声", 1),
       ("unk", "未知", 1)]
def classify_name(fname):
    low = fname.lower()
    for k, cn, lab in KEY:
        if k in low:
            return cn, lab
    return ("未识别", None)
cough_cnt, non_cnt = {}, {}
for cls_dir, lab in (("cough", 0), ("non_cough", 1)):
    for p in sorted((config.RAW_DIR / cls_dir).glob("*.wav")):
        cn, l2 = classify_name(p.name)
        if l2 == 0 or (l2 is None and lab == 0):
            cough_cnt[cn] = cough_cnt.get(cn, 0) + 1
        elif l2 == 1 or (l2 is None and lab == 1):
            non_cnt[cn] = non_cnt.get(cn, 0) + 1
# 重新归并：raw 的 cough 目录里一定都是咳嗽
cough_cnt, non_cnt = {}, {}
for p in sorted((config.RAW_DIR / "cough").glob("*.wav")):
    cn, _ = classify_name(p.name); cough_cnt[cn] = cough_cnt.get(cn, 0) + 1
for p in sorted((config.RAW_DIR / "non_cough").glob("*.wav")):
    cn, _ = classify_name(p.name); non_cnt[cn] = non_cnt.get(cn, 0) + 1

fig, ax = plt.subplots(1, 2, figsize=(13, 4.4))
ks = list(cough_cnt.keys()); vs = [cough_cnt[k] for k in ks]
b = ax[0].bar(ks, vs, color="#C44E52")
for bb, v in zip(b, vs): ax[0].text(bb.get_x()+bb.get_width()/2, v+1, str(v), ha="center", fontsize=9)
ax[0].set_title(f"(a) 咳嗽类样本分布（共 {sum(vs)} 个）"); ax[0].set_ylabel("样本数"); ax[0].grid(axis="y", alpha=0.3)
ks2 = list(non_cnt.keys()); vs2 = [non_cnt[k] for k in ks2]
b2 = ax[1].bar(ks2, vs2, color="#4C72B0")
for bb, v in zip(b2, vs2): ax[1].text(bb.get_x()+bb.get_width()/2, v+1, str(v), ha="center", fontsize=9)
ax[1].set_title(f"(b) 非咳嗽类样本分布（共 {sum(vs2)} 个）"); ax[1].set_ylabel("样本数"); ax[1].grid(axis="y", alpha=0.3)
plt.tight_layout(); fig.savefig(OUT / "fig5_数据集分布.png", dpi=200, bbox_inches="tight"); plt.close(fig)
print(f"已生成 fig5：咳嗽 {sum(vs)} / 非咳嗽 {sum(vs2)}")

# ---------- 图6：阈值-指标曲线（用原始文件级实测，最诚实） ----------
print("正在对全部原始音频做文件级概率扫描（约 1 分钟）...")
from src.inference import load_model, predict_segment
model = load_model()
probs, labels = [], []
for cls_dir, lab in (("cough", 0), ("non_cough", 1)):
    for p in sorted((config.RAW_DIR / cls_dir).glob("*.wav")):
        try:
            y, _ = load_audio(p, sr=SR)
            ypp = y
            ypp = bandpass_filter(ypp, sr=SR)
            ypp = pre_emphasis(ypp)
            ss = energy_endpoint_detect(ypp, sr=SR)
            # 关键：在预处理信号上"找段边界"，但取"原始波形"的切片（predict_segment 内部会再预处理一次，避免二次滤波）
            cand = [y[a:b] for a, b in ss] or [y]
            pmax = max(predict_segment(model, c, sr=SR)[0] for c in cand)
            probs.append(pmax); labels.append(lab)
        except Exception as e:
            print("  [warn]", p.name, e)
probs = np.array(probs); labels = np.array(labels)
ths = np.arange(0.05, 0.96, 0.05)
P, R, F = [], [], []
for th in ths:
    pred = np.where(probs >= th, 0, 1)
    tp = int(((pred == 0) & (labels == 0)).sum()); fp = int(((pred == 0) & (labels == 1)).sum()); fn = int(((pred == 1) & (labels == 0)).sum())
    p_ = tp / max(tp + fp, 1); r_ = tp / max(tp + fn, 1); f_ = 2 * p_ * r_ / max(p_ + r_, 1e-9)
    P.append(p_); R.append(r_); F.append(f_)
fig, ax = plt.subplots(figsize=(9.5, 4.8))
ax.plot(ths, P, "o-", label="精确率 Precision"); ax.plot(ths, R, "s-", label="召回率 Recall"); ax.plot(ths, F, "^-", label="F1")
best = int(np.argmax(F))
ax.axvline(ths[best], color="gray", ls="--", label=f"F1 最优阈值≈{ths[best]:.2f}（F1={F[best]:.3f}）")
ax.axvline(config.CONFIDENCE_THRESHOLD, color="red", ls=":", label=f"当前部署阈值={config.CONFIDENCE_THRESHOLD}")
ax.set_xlabel("判定阈值"); ax.set_ylabel("指标（文件级 %d 个音频）" % len(labels))
ax.set_title("阈值–指标权衡曲线（原始音频文件级实测：阈值越低越不漏检，但误报增多）")
ax.legend(fontsize=9); ax.grid(alpha=0.3)
plt.tight_layout(); fig.savefig(OUT / "fig6_阈值指标曲线.png", dpi=200, bbox_inches="tight"); plt.close(fig)
print(f"已生成 fig6（文件级实测 n={len(labels)}，F1最优阈值≈{ths[best]:.2f}）")

# ---------- 图7：模型结构 ----------
from src.model import build_and_compile
m = build_and_compile()
buf = io.StringIO(); m.summary(print_fn=lambda x: buf.write(x + "\n"))
(OUT / "fig7_模型结构.txt").write_text(buf.getvalue(), encoding="utf-8")
print("已生成 fig7")
print("\n全部输出:", OUT)