# -*- coding: utf-8 -*-
"""
16_tuned_run.py —— 按《关键图表解读与调参指南》调整参数，重跑一版做对比
原方案图片保留在 results/paper_figures/，本脚本输出到 results/paper_figures_tuned/

调参内容（依据指南）:
  ① 带通滤波放宽：100~2000 Hz  →  50~4000 Hz      （少丢掉咳嗽的高频成分）
  ② 梅尔滤波器上限：奈奎斯特(22050) → 4000 Hz，滤波器数 24 → 32（匹配 8kHz 数据带宽，提升有效频段分辨率）
  ③ 判定阈值：0.4 → 0.2                            （预警场景优先保召回，配合累计告警抑制误报）

运行: python scripts\16_tuned_run.py
输出: results/paper_figures_tuned/（fig1~fig8）
      results/tuned/（对比表 md、指标 json、对比图）
"""
import sys, io, json, glob
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
import tensorflow as tf

import config
from src.audio_io import load_audio
from src.preprocess import bandpass_filter, pre_emphasis, frame_signal, energy_endpoint_detect
from src.features import extract_mfcc, add_deltas, pad_or_truncate
from src.model import build_cnn_bilstm

SR = config.SAMPLE_RATE

# ---------------- 调参后的参数 ----------------
TUNED = dict(
    BP_LOW=50.0, BP_HIGH=4000.0,      # ① 带通放宽
    FMAX=4000.0, N_MELS=32,           # ② 梅尔上限与滤波器数
    THRESHOLD=0.2,                    # ③ 判定阈值
)
OUT_FIG = config.RESULT_DIR / "paper_figures_tuned"
OUT_DIR = config.RESULT_DIR / "tuned"
OUT_FIG.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)
print("调参方案:", TUNED)

# 原方案参数（用于图注对比）
ORIG = dict(BP_LOW=config.BANDPASS_LOW, BP_HIGH=config.BANDPASS_HIGH, FMAX=None, N_MELS=config.N_MELS)


def bp(y, low, high):
    return bandpass_filter(y, sr=SR, low=low, high=high, order=config.BUTTER_ORDER)


def feat_of(y, low, high, fmax, n_mels, n_mfcc=config.N_MFCC, use_delta=True):
    """按指定参数得到一条音频的特征（调用方负责先做端点检测/取值）"""
    m = extract_mfcc(y, sr=SR, n_mfcc=n_mfcc, n_fft=config.N_FFT,
                     hop_length=config.HOP_LENGTH, win_length=config.WIN_LENGTH,
                     n_mels=n_mels, fmax=fmax)
    f = add_deltas(m, use_delta=use_delta, use_delta2=use_delta) if use_delta else m
    return pad_or_truncate(f)


def pick(patterns):
    for pat in patterns:
        hits = sorted(glob.glob(str(config.RAW_DIR / pat)))
        if hits:
            return hits[0]
    return None


cough_path = pick(["cough/app_a.wav", "cough/flu_a.wav", "cough/*.wav"])
noncough_path = pick(["non_cough/gander_1.wav", "non_cough/norm_oink_1.wav", "non_cough/*.wav"])
print("样本:", Path(cough_path).name, "/", Path(noncough_path).name)

# ===========================================================================
# 一、生成调参版图片（fig1~fig7，原图保留）
# ===========================================================================
y_raw, _ = load_audio(cough_path, sr=SR)
y_bp_t = bp(y_raw, TUNED["BP_LOW"], TUNED["BP_HIGH"])
y_pe_t = pre_emphasis(y_bp_t)
y_bp_o = bp(y_raw, ORIG["BP_LOW"], ORIG["BP_HIGH"])
y_pe_o = pre_emphasis(y_bp_o)

# fig1：调参版预处理波形（并叠加原方案做对比）
t_axis = np.arange(len(y_raw)) / SR
fig, ax = plt.subplots(4, 1, figsize=(11, 9), sharex=True)
ax[0].plot(t_axis, y_raw, lw=0.7, color="#4C72B0"); ax[0].set_title("(a) 原始采集波形")
ax[1].plot(t_axis, y_pe_o, lw=0.7, color="#999999"); ax[1].set_title("(b) 原方案：带通 100~2000Hz + 预加重")
ax[2].plot(t_axis, y_pe_t, lw=0.7, color="#C44E52"); ax[2].set_title("(c) 调参方案：带通 50~4000Hz + 预加重（保留更多高频细节）")
ax[3].plot(t_axis, y_pe_t, lw=0.7, color="#C44E52", alpha=0.5, label="调参方案")
ax[3].plot(t_axis, y_pe_o, lw=0.7, color="#999999", alpha=0.5, label="原方案")
ax[3].set_title("(d) 两方案波形叠加对比"); ax[3].legend(fontsize=9)
for a in ax: a.set_ylabel("幅度"); a.grid(alpha=0.3)
ax[3].set_xlabel("时间 / s")
plt.tight_layout(); fig.savefig(OUT_FIG / "fig1_预处理对比_调参版.png", dpi=200, bbox_inches="tight"); plt.close(fig)
print("已生成 fig1（调参版）")

# fig2：调参版端点检测（能量与阈值随带通变化）
frames_t = frame_signal(y_pe_t, config.WIN_LENGTH, config.HOP_LENGTH)
e_t = np.sqrt((frames_t ** 2).mean(axis=1))
te_t = e_t.mean() + config.STE_THRESH_COEF * e_t.std()
segs_t = energy_endpoint_detect(y_pe_t, sr=SR)
fig, ax = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
ax[0].plot(t_axis, y_pe_t, lw=0.6, color="#C44E52")
for s, e in segs_t: ax[0].axvspan(s / SR, e / SR, color="orange", alpha=0.35)
ax[0].set_title("(a) 调参方案波形 + 端点检测有效段（橙色）"); ax[0].set_ylabel("幅度"); ax[0].grid(alpha=0.3)
tt = (np.arange(len(e_t)) * config.HOP_LENGTH + config.WIN_LENGTH / 2) / SR
ax[1].plot(tt, e_t, lw=1.0, color="#55A868", label="帧 RMS 能量 E(n)")
ax[1].axhline(te_t, color="#C44E52", ls="--", lw=1.5, label=f"自适应阈值 TE={te_t:.4f}")
ax[1].fill_between(tt, 0, e_t, where=e_t > te_t, color="orange", alpha=0.35)
ax[1].set_title("(b) 短时能量与自适应阈值"); ax[1].set_xlabel("时间 / s"); ax[1].set_ylabel("RMS"); ax[1].legend(); ax[1].grid(alpha=0.3)
plt.tight_layout(); fig.savefig(OUT_FIG / "fig2_端点检测_调参版.png", dpi=200, bbox_inches="tight"); plt.close(fig)
print(f"已生成 fig2（调参版，检出 {len(segs_t)} 段）")

# fig3：调参版 MFCC 对比（fmax=4000）
y_non, _ = load_audio(noncough_path, sr=SR)
y_non_t = pre_emphasis(bp(y_non, TUNED["BP_LOW"], TUNED["BP_HIGH"]))
m_c_t = extract_mfcc(y_pe_t, sr=SR, n_mels=TUNED["N_MELS"], fmax=TUNED["FMAX"]).T
m_n_t = extract_mfcc(y_non_t, sr=SR, n_mels=TUNED["N_MELS"], fmax=TUNED["FMAX"]).T
fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
im0 = ax[0].imshow(m_c_t, aspect="auto", origin="lower", cmap="viridis")
ax[0].set_title(f"(a) 咳嗽 MFCC（fmax={TUNED['FMAX']:.0f}Hz, {TUNED['N_MELS']} mel）")
ax[0].set_xlabel("帧"); ax[0].set_ylabel("MFCC 维数"); plt.colorbar(im0, ax=ax[0])
im1 = ax[1].imshow(m_n_t, aspect="auto", origin="lower", cmap="viridis")
ax[1].set_title("(b) 非咳嗽 MFCC（同参数）"); ax[1].set_xlabel("帧"); ax[1].set_ylabel("MFCC 维数"); plt.colorbar(im1, ax=ax[1])
plt.tight_layout(); fig.savefig(OUT_FIG / "fig3_MFCC对比_调参版.png", dpi=200, bbox_inches="tight"); plt.close(fig)
print("已生成 fig3（调参版）")

# fig4：调参版 39 维特征
f39_t = add_deltas(extract_mfcc(y_pe_t, sr=SR, n_mels=TUNED["N_MELS"], fmax=TUNED["FMAX"]))
fig, ax = plt.subplots(figsize=(11, 4.2))
im = ax.imshow(f39_t.T, aspect="auto", origin="lower", cmap="magma")
ax.set_title("调参方案 39 维特征矩阵（fmax=4000Hz、32 mel、带通 50~4000Hz）")
ax.set_xlabel("帧（10 ms/帧）"); ax.set_ylabel("39 维特征")
ax.axhline(12.5, color="w", ls="--", lw=1); ax.axhline(25.5, color="w", ls="--", lw=1)
plt.colorbar(im, ax=ax); plt.tight_layout(); fig.savefig(OUT_FIG / "fig4_39维特征_调参版.png", dpi=200, bbox_inches="tight"); plt.close(fig)
print("已生成 fig4（调参版）")

# fig5：数据分布（与原方案一致，复制一份便于对照）
import shutil
shutil.copy(config.RESULT_DIR / "paper_figures" / "fig5_数据集分布.png", OUT_FIG / "fig5_数据集分布.png")
print("已复制 fig5（数据分布不变）")

# fig7：模型结构（调参后特征维度不变，仍为 39 维）
m = build_cnn_bilstm()
buf = io.StringIO(); m.summary(print_fn=lambda x: buf.write(x + "\n"))
(OUT_FIG / "fig7_模型结构.txt").write_text(buf.getvalue(), encoding="utf-8")
print("已生成 fig7")

# ===========================================================================
# 二、用调参方案重训一个模型，做"文件级"指标与阈值曲线（与 fig6 同口径）
# ===========================================================================
print("\n正在用调参方案提取全部 540 个原始文件特征并训练对比模型 ...")
X, y = [], []
for cls_dir, lab in (("cough", 0), ("non_cough", 1)):
    for p in sorted((config.RAW_DIR / cls_dir).glob("*.wav")):
        try:
            yy, _ = load_audio(p, sr=SR)
            ypp = pre_emphasis(bp(yy, TUNED["BP_LOW"], TUNED["BP_HIGH"]))
            ss = energy_endpoint_detect(ypp, sr=SR)
            # 在预处理信号上找段边界，取原始波形切片（与生产链路一致，避免二次预处理）
            cands = [yy[a:b] for a, b in ss] or [yy]
            seg = max(cands, key=len)
            seg = bp(seg, TUNED["BP_LOW"], TUNED["BP_HIGH"])
            seg = pre_emphasis(seg)
            X.append(feat_of(seg, TUNED["BP_LOW"], TUNED["BP_HIGH"], TUNED["FMAX"], TUNED["N_MELS"]))
            y.append(lab)
        except Exception as e:
            print("  [warn]", p.name, e)
X = np.asarray(X, dtype=np.float32); y = np.asarray(y, dtype=np.int64)
print("特征集合:", X.shape)

from sklearn.model_selection import train_test_split
idx = np.arange(len(y))
i_tv, i_te = train_test_split(idx, test_size=0.1, random_state=config.SEED, stratify=y)
i_tr, i_va = train_test_split(i_tv, test_size=0.1 / 0.9, random_state=config.SEED, stratify=y[i_tv])
mean, std = X[i_tr].mean(axis=(0, 1)), X[i_tr].std(axis=(0, 1)) + 1e-6
Xn = (X - mean) / std

tf.keras.utils.set_random_seed(config.SEED)
model_t = build_cnn_bilstm(input_shape=(Xn.shape[1], Xn.shape[2], 1))
model_t.compile(optimizer=tf.keras.optimizers.Adam(config.LEARNING_RATE),
                loss="sparse_categorical_crossentropy", metrics=["accuracy"])
model_t.fit(Xn[i_tr][..., None], y[i_tr], validation_data=(Xn[i_va][..., None], y[i_va]),
            batch_size=config.BATCH_SIZE, epochs=25, verbose=0)
probs_t = model_t.predict(Xn[..., None], verbose=0)[:, 0]
np.savez_compressed(OUT_DIR / "tuned_scan.npz", probs=probs_t, labels=y)
print("调参模型训练完成")

def metrics_at(probs, labels, th):
    pred = np.where(probs >= th, 0, 1)
    tp = int(((pred == 0) & (labels == 0)).sum()); fp = int(((pred == 0) & (labels == 1)).sum())
    fn = int(((pred == 1) & (labels == 0)).sum()); tn = int(((pred == 1) & (labels == 1)).sum())
    p_ = tp / max(tp + fp, 1); r_ = tp / max(tp + fn, 1); f_ = 2 * p_ * r_ / max(p_ + r_, 1e-9)
    acc = (tp + tn) / max(len(labels), 1)
    return dict(acc=acc, precision=p_, recall=r_, f1=f_, fp=fp, fn=fn)

# fig8：调参版阈值曲线
ths = np.arange(0.05, 0.96, 0.05)
P, R, F = [], [], []
for th in ths:
    mm = metrics_at(probs_t, y, th); P.append(mm["precision"]); R.append(mm["recall"]); F.append(mm["f1"])
fig, ax = plt.subplots(figsize=(9.5, 4.8))
ax.plot(ths, P, "o-", label="精确率"); ax.plot(ths, R, "s-", label="召回率"); ax.plot(ths, F, "^-", label="F1")
best = int(np.argmax(F))
ax.axvline(ths[best], color="gray", ls="--", label=f"F1 最优阈值≈{ths[best]:.2f}")
ax.axvline(TUNED["THRESHOLD"], color="red", ls=":", label=f"调参后阈值={TUNED['THRESHOLD']}")
ax.set_xlabel("判定阈值"); ax.set_ylabel("指标（文件级 %d 个音频）" % len(y))
ax.set_title("调参方案 阈值–指标曲线（带通50~4000Hz / fmax4000 / 32mel）")
ax.legend(fontsize=9); ax.grid(alpha=0.3)
plt.tight_layout(); fig.savefig(OUT_FIG / "fig8_阈值指标曲线_调参版.png", dpi=200, bbox_inches="tight"); plt.close(fig)
print("已生成 fig8（调参版阈值曲线）")

# ===========================================================================
# 三、原方案 vs 调参方案 对比
# ===========================================================================
orig = np.load(config.RESULT_DIR / "paper_figures" / "threshold_scan.npz")
probs_o, labels_o = orig["probs"], orig["labels"]
rows = []
for th in (0.2, 0.4, 0.5):
    mo = metrics_at(probs_o, labels_o, th); mt = metrics_at(probs_t, y, th)
    rows.append((th, mo, mt))
cmp_lines = ["# 原方案 vs 调参方案（文件级实测，540 个原始音频）", "",
             "## 参数差异", "",
             "| 参数 | 原方案（照搬论文） | 调参方案 |", "|---|---|---|",
             f"| 带通滤波 | 100~2000 Hz | **50~4000 Hz** |",
             f"| 梅尔滤波器上限 fmax | 奈奎斯特（22050 Hz） | **4000 Hz**（匹配 8kHz 数据） |",
             f"| 梅尔滤波器数量 | 24 | **32** |",
             f"| 判定阈值 | 0.4 | **0.2** |", "",
             "## 指标对比（同一批 540 个文件、同一评估口径）", "",
             "| 阈值 | 方案 | 准确率 | 精确率 | 召回率 | F1 | 误报 | 漏检 |", "|---|---|---|---|---|---|---|---|"]
for th, mo, mt in rows:
    cmp_lines.append("| {} | 原方案 | {:.2%} | {:.2%} | {:.2%} | {:.3f} | {} | {} |".format(
        th, mo["acc"], mo["precision"], mo["recall"], mo["f1"], mo["fp"], mo["fn"]))
    cmp_lines.append("| {} | **调参方案** | {:.2%} | {:.2%} | {:.2%} | {:.3f} | {} | {} |".format(
        th, mt["acc"], mt["precision"], mt["recall"], mt["f1"], mt["fp"], mt["fn"]))
cmp_md = "\n".join(cmp_lines)
(OUT_DIR / "对比_原方案_vs_调参方案.md").write_text(cmp_md, encoding="utf-8")

# fig9：对比柱状图（阈值0.2 与 0.4 下的 P/R/F1）
fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))
for ax, (th, mo, mt) in zip(axes, [(0.4, rows[1][1], rows[1][2]), (0.2, rows[0][1], rows[0][2])]):
    xs = np.arange(3); w = 0.35
    o_v = [mo["precision"], mo["recall"], mo["f1"]]
    t_v = [mt["precision"], mt["recall"], mt["f1"]]
    b1 = ax.bar(xs - w / 2, o_v, w, label="原方案", color="#999999")
    b2 = ax.bar(xs + w / 2, t_v, w, label="调参方案", color="#C44E52")
    for bs in (b1, b2):
        for b in bs: ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.01, f"{b.get_height():.3f}", ha="center", fontsize=8)
    ax.set_xticks(xs); ax.set_xticklabels(["精确率", "召回率", "F1"]); ax.set_ylim(0, 1.12)
    ax.set_title(f"阈值 {th} 下的指标对比"); ax.legend(fontsize=9); ax.grid(axis="y", alpha=0.3)
plt.tight_layout(); fig.savefig(OUT_DIR / "fig9_对比_原方案vs调参方案.png", dpi=200, bbox_inches="tight"); plt.close(fig)
print("已生成 fig9（对比柱状图）")
print("\n" + cmp_md)
print("\n输出目录:", OUT_FIG, "|", OUT_DIR)