# -*- coding: utf-8 -*-
"""
14_ablation_study.py —— 消融实验（多种子重复，报告 均值±标准差）
对比组（每组只改一个变量，从原始音频走完整管线）:
  A 完整方案    带通(100~2000Hz)+预加重(0.97)+端点检测+MFCC(13+Δ+Δ²)+标准化
  B 去掉带通滤波 / C 去掉预加重 / D 去掉特征标准化 / E 仅 MFCC 13 维 / F 无端点检测

运行: python scripts\14_ablation_study.py --epochs 20 --seeds 3
输出: results/ablation/ablation_results.md / .csv
"""
import sys, io, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import numpy as np
import tensorflow as tf

import config
from src.audio_io import load_audio
from src.preprocess import bandpass_filter, pre_emphasis, energy_endpoint_detect
from src.features import extract_mfcc, add_deltas, pad_or_truncate
from src.model import build_cnn_bilstm
from src.evaluate import compute_metrics

OUT = config.RESULT_DIR / "ablation"
OUT.mkdir(parents=True, exist_ok=True)
SR = config.SAMPLE_RATE


def list_raw():
    items = []
    for cls_name, label in (("cough", 0), ("non_cough", 1)):
        for p in sorted((config.RAW_DIR / cls_name).glob("*.wav")):
            items.append((p, label))
    return items


def featurize(path, use_bandpass=True, use_preemphasis=True, use_delta=True, use_endpoint=True):
    y, _ = load_audio(path, sr=SR)
    yp = y
    if use_bandpass: yp = bandpass_filter(yp, sr=SR)
    if use_preemphasis: yp = pre_emphasis(yp)
    if use_endpoint:
        segs = energy_endpoint_detect(yp, sr=SR)
        if segs:
            s, e = segs[0]; yp = yp[s:e]
    mfcc = extract_mfcc(yp, sr=SR)
    feat = add_deltas(mfcc, use_delta=True, use_delta2=True) if use_delta else mfcc
    return pad_or_truncate(feat)


def build_dataset(items, **kw):
    X, y = [], []
    for p, label in items:
        try:
            X.append(featurize(p, **kw)); y.append(label)
        except Exception as e:
            print("  [warn]", p.name, e)
    return np.asarray(X, dtype=np.float32), np.asarray(y, dtype=np.int64)


def split_rows(y, seed, val=0.1, test=0.1):
    from sklearn.model_selection import train_test_split
    idx = np.arange(len(y))
    i_tv, i_te = train_test_split(idx, test_size=test, random_state=seed, stratify=y)
    i_tr, i_va = train_test_split(i_tv, test_size=val/(1-test), random_state=seed, stratify=y[i_tv])
    return i_tr, i_va, i_te


def one_run(X, y, seed, epochs, use_norm=True):
    i_tr, i_va, i_te = split_rows(y, seed)
    Xn = X.copy()
    if use_norm:
        mean, std = Xn[i_tr].mean(axis=(0, 1)), Xn[i_tr].std(axis=(0, 1)) + 1e-6
        Xn = (Xn - mean) / std
    tf.keras.utils.set_random_seed(seed)
    model = build_cnn_bilstm(input_shape=(Xn.shape[1], Xn.shape[2], 1))
    model.compile(optimizer=tf.keras.optimizers.Adam(config.LEARNING_RATE),
                  loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    model.fit(Xn[i_tr][..., None], y[i_tr], validation_data=(Xn[i_va][..., None], y[i_va]),
              batch_size=config.BATCH_SIZE, epochs=epochs, verbose=0)
    pred = np.argmax(model.predict(Xn[i_te][..., None], verbose=0), axis=1)
    return compute_metrics(y[i_te], pred)


def run_variant(name, items, epochs, seeds, use_norm=True, **kw):
    print(f"\n===== {name} =====")
    X, y = build_dataset(items, **kw)
    res = [one_run(X, y, s, epochs, use_norm=use_norm) for s in seeds]
    acc = [r["accuracy"] for r in res]; f1 = [r["f1"] for r in res]
    p = [r["precision"] for r in res]; r_ = [r["recall"] for r in res]
    print(f"  样本 {len(y)}，特征 {X.shape[1:]}；{len(seeds)} 次重复: "
          f"Acc={np.mean(acc)*100:.2f}±{np.std(acc)*100:.2f}%  F1={np.mean(f1)*100:.2f}±{np.std(f1)*100:.2f}%")
    return dict(variant=name, n=len(y), dim=X.shape[-1],
                acc_mean=np.mean(acc), acc_std=np.std(acc),
                pre_mean=np.mean(p), pre_std=np.std(p),
                rec_mean=np.mean(r_), rec_std=np.std(r_),
                f1_mean=np.mean(f1), f1_std=np.std(f1))


def main(args):
    items = list_raw()
    seeds = [config.SEED + i for i in range(args.seeds)]
    e = args.epochs
    rows = [
        run_variant("A 完整方案", items, e, seeds, use_norm=True),
        run_variant("B 去掉带通滤波", items, e, seeds, use_norm=True, use_bandpass=False),
        run_variant("C 去掉预加重", items, e, seeds, use_norm=True, use_preemphasis=False),
        run_variant("D 去掉特征标准化", items, e, seeds, use_norm=False),
        run_variant("E 仅 MFCC 13 维", items, e, seeds, use_norm=True, use_delta=False),
        run_variant("F 无端点检测（整段）", items, e, seeds, use_norm=True, use_endpoint=False),
    ]
    L = [f"# 消融实验结果（每组仅改一个变量；训练 {e} 轮；{len(seeds)} 个随机种子重复）", "",
         "| 方案 | 样本数 | 特征维度 | 准确率(均值±标准差) | 精确率 | 召回率 | F1(均值±标准差) |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append("| {} | {} | {} | {:.2%} ± {:.2%} | {:.2%} ± {:.2%} | {:.2%} ± {:.2%} | {:.2%} ± {:.2%} |".format(
            r["variant"], r["n"], r["dim"], r["acc_mean"], r["acc_std"], r["pre_mean"], r["pre_std"],
            r["rec_mean"], r["rec_std"], r["f1_mean"], r["f1_std"]))
    L += ["", "> 说明：①A 为完整方案，其余行去掉某一环节；②小样本下单次结果波动大，故用多种子重复报告均值±标准差；",
          "> ③标准差越小说明该方案越稳定。若去掉某环节后均值下降且标准差不大，说明该环节确有贡献。"]
    md = "\n".join(L)
    (OUT / "ablation_results.md").write_text(md, encoding="utf-8")
    import csv
    with open(OUT / "ablation_results.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader()
        for r in rows: w.writerow(r)
    print("\n" + md)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--seeds", type=int, default=3)
    main(ap.parse_args())