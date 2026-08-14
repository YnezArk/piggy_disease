import os
import json
import numpy as np
import librosa
import pymysql
from datetime import datetime

# ============================================================
# 1. 配置区域
# ============================================================

# ★ 使用相对路径：脚本所在目录下的 pig_cough_data 文件夹
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # 获取脚本所在目录
AUDIO_ROOT = os.path.join(BASE_DIR, "pig_cough_data")  # 音频数据目录

# ★ 数据库连接信息
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'asus',
    'database': 'pig_cough',
    'charset': 'utf8mb4'
}

# ★ 特征提取参数
SAMPLE_RATE = 16000
DURATION = 1.0
N_MFCC = 13
N_FFT = 2048
HOP_LENGTH = 512

# ★ 标签与疾病ID的映射（五分类）
# 2026-08-14 文件夹已重命名与 pig_diag_v2.disease.label 对齐：swine_influenza→influenza、contagious_pleuropneumonia→app
LABEL_MAP = {
    "normal": 1,
    "influenza": 2,
    "prrs": 3,
    "mycoplasma": 4,
    "app": 5
}

FEATURE_TYPES = ['MFCC', 'logFBank', '时域特征', '频域特征']


# ============================================================
# 2. 特征提取函数
# ============================================================

def extract_features(file_path):
    y, sr = librosa.load(file_path, sr=SAMPLE_RATE, duration=DURATION)
    if len(y) < sr * DURATION:
        y = np.pad(y, (0, int(sr * DURATION) - len(y)))

    features = {}
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=N_MFCC, n_fft=N_FFT, hop_length=HOP_LENGTH)
    features['MFCC'] = np.mean(mfcc, axis=1).tolist()

    mel_spec = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=64, n_fft=N_FFT, hop_length=HOP_LENGTH)
    log_mel = librosa.power_to_db(mel_spec, ref=np.max)
    features['logFBank'] = np.mean(log_mel, axis=1).tolist()

    energy = np.sum(y ** 2) / len(y)
    zcr = np.mean(librosa.feature.zero_crossing_rate(y)[0])
    rms = np.mean(librosa.feature.rms(y=y)[0])
    features['时域特征'] = [float(energy), float(zcr), float(rms)]

    spec_cent = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)[0])
    spec_bw = np.mean(librosa.feature.spectral_bandwidth(y=y, sr=sr)[0])
    spec_flat = np.mean(librosa.feature.spectral_flatness(y=y)[0])
    spec_roll = np.mean(librosa.feature.spectral_rolloff(y=y, sr=sr)[0])
    features['频域特征'] = [float(spec_cent), float(spec_bw), float(spec_flat), float(spec_roll)]
    return features


# ============================================================
# 3. 主程序
# ============================================================

def main():
    print(f"📁 脚本所在目录: {BASE_DIR}")
    print(f"📁 音频数据目录: {AUDIO_ROOT}")

    # 检查音频目录是否存在
    if not os.path.exists(AUDIO_ROOT):
        print(f"❌ 错误：音频目录不存在！请检查 {AUDIO_ROOT}")
        return

    # 连接数据库
    conn = pymysql.connect(
        host=DB_CONFIG['host'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        database=DB_CONFIG['database'],
        charset=DB_CONFIG['charset']
    )
    cursor = conn.cursor()
    total_inserted = 0

    for label, disease_id in LABEL_MAP.items():
        folder_path = os.path.join(AUDIO_ROOT, label)
        if not os.path.exists(folder_path):
            print(f"⚠️ 警告：文件夹 {folder_path} 不存在，已跳过")
            continue

        wav_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.wav')]
        print(f"📂 正在处理 {label} 文件夹，共 {len(wav_files)} 个文件...")

        for filename in wav_files:
            file_path = os.path.join(folder_path, filename)
            try:
                feat_dict = extract_features(file_path)

                cough_type = label
                raw_symptom = f"人工分类：{label}，文件名：{filename}"

                sql_diagnosis = """
                    INSERT INTO diagnosis_records 
                    (group_id, disease_id, cough_type, raw_symptoms, diagnosis_time, model_version)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql_diagnosis, (
                    1, disease_id, cough_type, raw_symptom, datetime.now(), 'manual_v5'
                ))
                record_id = cursor.lastrowid

                for feat_type in FEATURE_TYPES:
                    if feat_type in feat_dict:
                        vector_json = json.dumps(feat_dict[feat_type])
                        cursor.execute("""
                            INSERT INTO acoustic_features 
                            (record_id, feature_type, feature_dimension, feature_vector)
                            VALUES (%s, %s, %s, %s)
                        """, (record_id, feat_type, len(feat_dict[feat_type]), vector_json))

                total_inserted += 1
                print(f"   ✅ 已处理: {filename} -> record_id={record_id}, disease={label}")

            except Exception as e:
                print(f"   ❌ 处理 {filename} 时出错: {e}")
                conn.rollback()
                continue

            if total_inserted % 10 == 0:
                conn.commit()
                print(f"   📝 已提交 {total_inserted} 条记录...")

    conn.commit()
    print(f"\n🎉 全部完成！共插入 {total_inserted} 条诊断记录。")
    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()

