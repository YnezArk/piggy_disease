# -*- coding: utf-8 -*-
"""
17_fair_compare.py —— 严格公平对比：原方案 vs 调参方案
两方案使用完全相同的：文件集合、8:1:1 划分（seed=42）、模型结构、训练轮数、评估口径；
只在【留出的测试集】上评估（模型没见过），结论更可信。
输出: results/tuned/公平对比_测试集.md + fig_公平对比.png
"""
import sys, io
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
from sklearn.model_selection import train_test_split

import config
from src.audio_io import load_audio
from src.preprocess import bandpass_filter, pre_emphasis, energy_endpoint_detect
from src.features import extract_mfcc, add_deltas, pad_or_truncate
from src.model import build_cnn_bilstm

SR = config.SAMPLE_RATE
OUT = config.RESULT_DIR / "tuned"
OUT.mkdir(parents=True, exist_ok=True)

SCHEMES = {
    "原方案（照搬论文）": dict(low=100.0, high=2000.0, fmax=None, n_mels=24),
    "调参方案": dict(low=50.0, high=4000.0, fmax=4000.0, n_mels=32),
}
EPOCHS = 25


def extract_features(scheme):
    X, y, names = [], [], []
    for cls_dir, lab in (("cough", 0), ("non_cough", 1)):
        for p in sorted((config.RAW_DIR / cls_dir).glob("*.wav")):
            try:
                yy, _ = load_audio(p, sr=SR)
                ypp = pre_emphasis(bandpass_filter(yy, sr=SR, low=scheme["low"], high=scheme["high"]))
                ss = energy_endpoint_detect(ypp, sr=SR)
                cands = [yy[a:b] for a, b in ss] or [yy]
                seg = max(cands, key=len)
                seg = bandpass_filter(seg, sr=SR, low=scheme["low"], high=scheme["high"])
                seg = pre_emphasis(seg)
                m = extract_mfcc(seg, sr=SR, n_mels=scheme["n_mels"], fmax=scheme["fmax"])
                feat = add_deltas(m)
                X.append(pad_or_truncate(feat)); y.append(lab); names.append(p.name)
            except Exception as e:
                print("  [warn]", p.name, e)
    return np.asarray(X, dtype=np.float32), np.asarray(y, dtype=np.int64), names


def run_scheme(name, scheme):
    print(f"\n===== {name} =====")
    X, y, names = extract_features(scheme)
    idx = np.arange(len(y))
    i_tv, i_te = train_test_split(idx, test_size=0.1, random_state=config.SEED, stratify=y)
    i_tr, i_va = train_test_split(i_tv, test_size=0.1/0.9, random_state=config.SEED, stratify=y[i_tv])
    mean, std = X[i_tr].mean(axis=(0, 1)), X[i_tr].std(axis=(0, 1)) + 1e-6
    Xn = (X - mean) / std
    tf.keras.utils.set_random_seed(config.SEED)
    model = build_cnn_bilstm(input_shape=(Xn.shape[1], Xn.shape[2], 1))
    model.compile(optimizer=tf.keras.optimizers.Adam(config.LEARNING_RATE),
                  loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    model.fit(Xn[i_tr][..., None], y[i_tr], validation_data=(Xn[i_va][..., None], y[i_va]),
              batch_size=config.BATCH_SIZE, epochs=EPOCHS, verbose=0)
    probs = model.predict(Xn[..., None], verbose=0)[:, 0]
    res = {}
    for th in (0.2, 0.4, 0.5):
        pred = np.where(probs[i_te] >= th, 0, 1); yte = y[i_te]
        tp = int(((pred == 0) & (yte == 0)).sum()); fp = int(((pred == 0) & (yte == 1)).sum())
        fn = int(((pred == 1) & (yte == 0)).sum()); tn = int(((pred == 1) & (yte == 1)).sum())
        p_ = tp/max(tp+fp,1); r_ = tp/max(tp+fn,1); f_ = 2*p_*r_/max(p_+r_,1e-9)
        res[th] = dict(acc=(tp+tn)/len(yte), precision=p_, recall=r_, f1=f_, fp=fp, fn=fn)
        print(f"  阈值{th}: Acc={res[th]['acc']*100:.2f}% P={p_*100:.2f}% R={r_*100:.2f}% F1={f_:.3f} 误报={fp} 漏检={fn}")
    return res, len(y), len(i_te), probs, y, i_te


r_orig, n_all, n_test, probs_o, y_all, i_te = run_scheme("原方案（照搬论文）", SCHEMES["原方案（照搬论文）"])
r_tune, _, _, probs_t, _, _ = run_scheme("调参方案", SCHEMES["调参方案"])

L = [f"# 严格公平对比：原方案 vs 调参方案（仅在留出测试集上评估）", "",
     f"- 文件总数：{n_all}（咳嗽 {int((y_all==0).sum())} / 非咳嗽 {int((y_all==1).sum())}）",
     f"- 划分：8:1:1 分层（seed={config.SEED}），**测试集 {n_test} 个文件，两方案完全相同**",
     f"- 模型结构/训练轮数完全相同（CNN-BiLSTM，{EPOCHS} 轮，特征标准化）", "",
     "## 参数差异", "", "| 参数 | 原方案 | 调参方案 |", "|---|---|---|",
     "| 带通滤波 | 100~2000 Hz | **50~4000 Hz** |",
     "| 梅尔滤波器上限 | 奈奎斯特 22050 Hz | **4000 Hz** |",
     "| 梅尔滤波器数量 | 24 | **32** |", "",
     "## 测试集指标对比", "",
     "| 阈值 | 方案 | 准确率 | 精确率 | 召回率 | F1 | 误报 | 漏检 |", "|---|---|---|---|---|---|---|---|"]
for th in (0.2, 0.4, 0.5):
    for nm, rr in (("原方案", r_orig[th]), ("**调参方案**", r_tune[th])):
        L.append("| {} | {} | {:.2%} | {:.2%} | {:.2%} | {:.3f} | {} | {} |".format(
            th, nm, rr["acc"], rr["precision"], rr["recall"], rr["f1"], rr["fp"], rr["fn"]))
L += ["", "> 说明：左右两行使用同一测试集、同一模型结构、同一训练轮数，唯一差别是预处理/特征参数，因此差异可归因于调参本身。"]
md = "\n".join(L)
(OUT / "公平对比_测试集.md").write_text(md, encoding="utf-8")
print("\n" + md)

fig, axes = plt.subplots(1, 3, figsize=(14, 4.2))
for ax, th in zip(axes, (0.2, 0.4, 0.5)):
    xs = np.arange(3); w = 0.35
    ov = [r_orig[th]["precision"], r_orig[th]["recall"], r_orig[th]["f1"]]
    tv = [r_tune[th]["precision"], r_tune[th]["recall"], r_tune[th]["f1"]]
    b1 = ax.bar(xs - w/2, ov, w, label="原方案", color="#999999")
    b2 = ax.bar(xs + w/2, tv, w, label="调参方案", color="#C44E52")
    for bs in (b1, b2):
        for b in bs:
            ax.text(b.get_x()+b.get_width()/2, b.get_height()+0.01, f"{b.get_height():.3f}", ha="center", fontsize=8)
    ax.set_xticks(xs); ax.set_xticklabels(["精确率", "召回率", "F1"]); ax.set_ylim(0, 1.15)
    ax.set_title(f"阈值 {th}（留出测试集 n={n_test}）"); ax.legend(fontsize=9); ax.grid(axis="y", alpha=0.3)
plt.suptitle("原方案 vs 调参方案：留出测试集公平对比", fontsize=13)
plt.tight_layout(); fig.savefig(OUT / "fig_公平对比_测试集.png", dpi=200, bbox_inches="tight"); plt.close(fig)
print("已生成对比图:", OUT / "fig_公平对比_测试集.png")