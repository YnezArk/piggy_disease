# -*- coding: utf-8 -*-
"""
辨病模块 — 统一特征管线（与 pig_diag_v2.acoustic_feature 库内口径完全一致）

功能：
  1. extract_features(path)     单条音频 → 84 维特征（与入库脚本逐参数一致）
  2. build_feature_matrix()     全量提取 198 条标注样本 → (X, y, file_ids)
  3. verify_db()                与库内 acoustic_feature 复算校验（误差 < 1e-6）
  4. split_dataset()            8:1:1 分层划分 → features/*.npz + 落库 training_dataset

范围（2026-08-14）：仅 5 类有标注数据的疾病（normal/influenza/prrs/mycoplasma/app），
猪肺疫/混合感染等其余类别在未来开发中完善。

用法：
  python features.py extract      # 提取 + 复算校验
  python features.py verify       # 仅复算校验
  python features.py split        # 数据划分 + npz + 落库
"""
import os
import sys
import json

import numpy as np

# 与 extract_and_insert（提取特征的脚本）.py 完全一致的提取参数
SAMPLE_RATE = 16000      # 源音频 8kHz，加载时重采样
DURATION = 1.0           # 统一时长（截断/零填充）
N_MFCC = 13
N_FFT = 2048
HOP_LENGTH = 512

# 有标注数据的 5 类（key = 文件夹名 = disease.label）
LABEL_MAP = {"normal": 1, "influenza": 2, "prrs": 3, "mycoplasma": 4, "app": 5}
LABEL_NAMES = list(LABEL_MAP.keys())          # 顺序即类别索引（0-based label）
FEATURE_NAMES = ["mfcc", "logfbank", "temporal", "spectral"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_ROOT = os.path.join(BASE_DIR, "pig_cough_data")
FEAT_DIR = os.path.join(BASE_DIR, "features")

# 数据库连接（与根目录 .env / config.py 一致）
DB_CONFIG = dict(host="localhost", user="root", password="36987412",
                 database="pig_diag_v2", charset="utf8mb4")


def extract_features_ext(file_path):
    """单条音频 → 142 维扩展特征（消融实验用）：
    MFCC 13+Δ+Δ²（均值+标准差 78 维）+ logFBank 64 均值 = 142 维
    """
    import librosa
    y, sr = librosa.load(file_path, sr=SAMPLE_RATE, duration=DURATION)
    if len(y) < sr * DURATION:
        y = np.pad(y, (0, int(sr * DURATION) - len(y)))
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=N_MFCC, n_fft=N_FFT, hop_length=HOP_LENGTH)
    d1 = librosa.feature.delta(mfcc)
    d2 = librosa.feature.delta(mfcc, order=2)
    mfcc_all = np.vstack([mfcc, d1, d2])                      # (39, T)
    mel = librosa.power_to_db(
        librosa.feature.melspectrogram(y=y, sr=sr, n_mels=64, n_fft=N_FFT, hop_length=HOP_LENGTH),
        ref=np.max)
    return np.concatenate([mfcc_all.mean(axis=1), mfcc_all.std(axis=1),
                           mel.mean(axis=1)]).astype(np.float64)   # 39+39+64=142


def build_feature_matrix_ext():
    """142 维扩展特征全量提取，文件顺序与 build_feature_matrix 完全一致（索引可对齐）。"""
    X, y, file_ids = build_feature_matrix()   # 复用顺序与标签
    Xe = np.zeros((len(file_ids), 142))
    for i, src in enumerate(file_ids):
        Xe[i] = extract_features_ext(os.path.join(AUDIO_ROOT, src))
    return Xe, y, file_ids


def extract_features(file_path):
    """单条音频 → 84 维特征（均值池化），与库内口径逐参数一致。"""
    import librosa
    y, sr = librosa.load(file_path, sr=SAMPLE_RATE, duration=DURATION)
    if len(y) < sr * DURATION:
        y = np.pad(y, (0, int(sr * DURATION) - len(y)))

    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=N_MFCC, n_fft=N_FFT, hop_length=HOP_LENGTH)
    mel_spec = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=64, n_fft=N_FFT, hop_length=HOP_LENGTH)
    log_mel = librosa.power_to_db(mel_spec, ref=np.max)

    energy = np.sum(y ** 2) / len(y)
    zcr = np.mean(librosa.feature.zero_crossing_rate(y)[0])
    rms = np.mean(librosa.feature.rms(y=y)[0])

    spec_cent = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)[0])
    spec_bw = np.mean(librosa.feature.spectral_bandwidth(y=y, sr=sr)[0])
    spec_flat = np.mean(librosa.feature.spectral_flatness(y=y)[0])
    spec_roll = np.mean(librosa.feature.spectral_rolloff(y=y, sr=sr)[0])

    return {
        "mfcc": np.mean(mfcc, axis=1).astype(np.float64),
        "logfbank": np.mean(log_mel, axis=1).astype(np.float64),
        "temporal": np.array([float(energy), float(zcr), float(rms)]),
        "spectral": np.array([float(spec_cent), float(spec_bw), float(spec_flat), float(spec_roll)]),
    }


def build_feature_matrix():
    """全量提取 5 类标注样本 → X(198,84), y(198,), file_ids(198,)。"""
    import librosa  # 延迟导入，verify-only 场景不依赖音频

    X, y, file_ids = [], [], []
    for label in LABEL_NAMES:
        folder = os.path.join(AUDIO_ROOT, label)
        if not os.path.isdir(folder):
            print(f"⚠️ 缺文件夹: {label}，跳过")
            continue
        files = sorted(f for f in os.listdir(folder) if f.lower().endswith(".wav"))
        for fn in files:
            feat = extract_features(os.path.join(folder, fn))
            X.append(np.concatenate([feat[k] for k in FEATURE_NAMES]))  # (84,)
            y.append(LABEL_MAP[label] - 1)                              # 0-based
            file_ids.append(f"{label}/{fn}")
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y, dtype=np.int64)
    return X, y, np.asarray(file_ids)


def _fetch_db_features():
    """读库内 acoustic_feature 宽表 → {file_source: {type: np.array}}。"""
    import pymysql
    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("""
        SELECT r.file_source, a.mfcc, a.logfbank, a.temporal, a.spectral
        FROM acoustic_feature a JOIN diagnosis_record r ON a.diagnosis_id = r.id
        WHERE r.id >= 371 AND r.file_source IS NOT NULL
    """)
    out = {}
    for src, m, f, t, s in cur.fetchall():
        out[src] = {"mfcc": np.array(json.loads(m), dtype=np.float64),
                    "logfbank": np.array(json.loads(f), dtype=np.float64),
                    "temporal": np.array(json.loads(t), dtype=np.float64),
                    "spectral": np.array(json.loads(s), dtype=np.float64)}
    conn.close()
    return out


def verify_db():
    """复算校验：features.py 提取 vs 库内存储，逐文件逐类型最大绝对误差。"""
    db = _fetch_db_features()
    print(f"库内样本数: {len(db)}")

    per_type_max = {k: 0.0 for k in FEATURE_NAMES}
    per_type_count = {k: 0 for k in FEATURE_NAMES}
    worst = []  # (file, type, err)

    for label in LABEL_NAMES:
        folder = os.path.join(AUDIO_ROOT, label)
        files = sorted(f for f in os.listdir(folder) if f.lower().endswith(".wav"))
        for fn in files:
            src = f"{label}/{fn}"
            if src not in db:
                print(f"⚠️ 库内无此样本: {src}")
                continue
            feat = extract_features(os.path.join(folder, fn))
            for k in FEATURE_NAMES:
                err = float(np.max(np.abs(feat[k] - db[src][k])))
                per_type_max[k] = max(per_type_max[k], err)
                per_type_count[k] += 1
                if err > 1e-6:
                    worst.append((src, k, err))

    print("\n=== 复算校验结果 ===")
    for k in FEATURE_NAMES:
        print(f"  {k:10s} 对比 {per_type_count[k]} 条, 最大绝对误差: {per_type_max[k]:.2e}")
    bad = [w for w in worst if w[2] > 1e-6]
    if bad:
        bad.sort(key=lambda x: -x[2])
        print(f"\n⚠️ 超差 {len(bad)} 条（>1e-6），前 5 条：")
        for src, k, err in bad[:5]:
            print(f"   {src} [{k}] err={err:.2e}")
        return False
    print("\n✅ 全部 198 条与库内一致（误差 < 1e-6），特征管线可复算")
    return True


def split_dataset(seed=42):
    """8:1:1 分层划分 → features/*.npz（X, y, file_id）+ 落库 training_dataset。"""
    from sklearn.model_selection import train_test_split
    import pymysql

    X, y, file_ids = build_feature_matrix()
    print(f"全量: {X.shape}, 标签分布: {dict(zip(*np.unique(y, return_counts=True)))}")

    tr_idx, te_idx = train_test_split(np.arange(len(y)), test_size=0.1,
                                      random_state=seed, stratify=y)
    y_tr, y_te = y[tr_idx], y[te_idx]
    tr_idx, va_idx = train_test_split(tr_idx, test_size=1/9,  # 0.9×1/9 = 0.1
                                      random_state=seed, stratify=y_tr)
    parts = {"train": tr_idx, "val": va_idx, "test": te_idx}

    os.makedirs(FEAT_DIR, exist_ok=True)
    for name, idx in parts.items():
        np.savez(os.path.join(FEAT_DIR, f"features_{name}.npz"),
                 X=X[idx], y=y[idx], file_id=file_ids[idx], label_names=np.asarray(LABEL_NAMES))
        dist = dict(zip(*np.unique(y[idx], return_counts=True)))
        print(f"  {name:5s}: {len(idx)} 条, 标签分布 {dist}")

    # 落库 training_dataset
    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO training_dataset (dataset_name, dataset_type, description,
            record_ids, total_samples, label_distribution, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, ("辨病_8_1_1_v2", "诊断",
          "新数据集(299条)8:1:1分层划分，random_state=42；X=84维(13+64+3+4)均值池化；file_source 可追溯",
          json.dumps({k: v.tolist() for k, v in parts.items()}, ensure_ascii=False),
          int(len(y)),
          json.dumps({int(k): int(v) for k, v in zip(*np.unique(y, return_counts=True))},
                     ensure_ascii=False),
          "阴学舟"))
    conn.commit()
    conn.close()
    print("\n✅ 划分完成并落库 training_dataset")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "verify"
    if mode == "extract":
        X, y, fids = build_feature_matrix()
        print(f"提取完成: X={X.shape}, y={y.shape}, 样本 {len(fids)} 条")
        verify_db()
    elif mode == "verify":
        verify_db()
    elif mode == "split":
        split_dataset()
    elif mode == "extract_ext":
        # 142 维扩展特征：按 8:1:1 划分的索引切出 ext npz（与 84 维划分一致）
        import numpy as _np
        Xe, y, fids = build_feature_matrix_ext()
        os.makedirs(FEAT_DIR, exist_ok=True)
        for name in ["train", "val", "test"]:
            d = _np.load(os.path.join(FEAT_DIR, f"features_{name}.npz"))
            idx = [list(fids).index(f) for f in d["file_id"]]   # 按 file_id 对齐索引
            _np.savez(os.path.join(FEAT_DIR, f"features_ext_{name}.npz"),
                      X=Xe[idx], y=d["y"], file_id=d["file_id"], label_names=_np.asarray(LABEL_NAMES))
        print(f"142 维扩展特征已保存: features_ext_{{train,val,test}}.npz, X={Xe.shape}")
    else:
        print(__doc__)
