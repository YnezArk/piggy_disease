# -*- coding: utf-8 -*-
"""全局配置：音频参数 / 预处理参数 / 特征参数 / 模型超参数 / 监测预警参数 / 路径 / 数据库。

路径全部相对项目根目录，数据库/接口密钥从根目录 .env 读取。
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent          # monitor/
ROOT_DIR = BASE_DIR.parent                          # 项目根目录
load_dotenv(ROOT_DIR / ".env")

DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw" / "monitor"
PROCESSED_DIR = DATA_DIR / "processed" / "monitor"
FEATURE_DIR = DATA_DIR / "features" / "monitor"
MODEL_DIR = ROOT_DIR / "models" / "monitor"
RESULT_DIR = ROOT_DIR / "results" / "monitor"
SQL_DIR = DATA_DIR / "sql"

# ===========================================================================
# 数据库对接（MySQL：pig_cough_dataset 库）
# ===========================================================================
DB_ENABLED = True                 # 是否从数据库读取样本清单/标签（连不上时自动回退本地目录扫描）
DB_HOST = os.environ.get("DB_HOST", "127.0.0.1")
DB_PORT = int(os.environ.get("DB_PORT", "3306"))
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASS", "")
DB_NAME = os.environ.get("MONITOR_DB_NAME", "pig_cough_dataset")
DB_CHARSET = "utf8mb4"

# 本地音频根目录：数据库的 audio_filename / relative_path 相对该目录解析到真实文件
AUDIO_ROOT = RAW_DIR

# relative_path 顶层目录 -> 你本地目录 的映射
# （同学交付结构是 positive/negative，你本地用的是 cough/non_cough）
DB_PATH_MAP = {"cough": "cough", "non-cough": "non_cough",
               "positive": "cough", "negative": "non_cough"}

# 数据集划分后是否把 dataset_split(1训练/2验证/3测试) 写回数据库 audio_sample 表
DB_WRITE_SPLIT_BACK = False

# ===========================================================================
# 音频参数
# ===========================================================================
SAMPLE_RATE = 44100
CHANNELS = 1

# 预处理参数（设计文档 3.2 节 / 付小朋等）
BANDPASS_LOW = 100.0
BANDPASS_HIGH = 2000.0
BUTTER_ORDER = 4
PRE_EMPHASIS_ALPHA = 0.97
FRAME_LEN_MS = 25.0
FRAME_SHIFT_MS = 10.0
WINDOW = "hamming"
STE_THRESH_COEF = 0.5
MIN_SEGMENT_SEC = 0.2
MAX_SEGMENT_SEC = 1.5

# 特征提取参数（设计文档 3.3 节）
N_MFCC = 13
N_MELS = 24
# FFT 点数：必须 >= 帧长(win_length=1102)。论文写的 512 与 25ms/44.1kHz 帧长相矛盾，
# 这里取 2048（零填充），仍满足"分帧 25ms / 帧移 10ms"。
N_FFT = 2048
USE_DELTA = True
USE_DELTA2 = True
N_FEATURES = N_MFCC * (1 + int(USE_DELTA) + int(USE_DELTA2))

SEGMENT_SEC = 1.0
HOP_LENGTH = int(SAMPLE_RATE * FRAME_SHIFT_MS / 1000)
WIN_LENGTH = int(SAMPLE_RATE * FRAME_LEN_MS / 1000)
# librosa 对 1 秒信号（center=True 补齐）实际产生 101 帧，这里与之对齐
N_FRAMES = 101

# 数据增强（设计文档 3.5 节）
AUGMENT = True
AUGMENT_TRAIN = True          # 训练阶段是否对每段做波形域增强（在 02 特征提取时）
AUGMENT_TIMES = 2
TIME_STRETCH_RANGE = (0.9, 1.1)
PITCH_SHIFT_RANGE = (-2, 2)
NOISE_SNR_DB = (5.0, 15.0)

# 模型与训练超参数（设计文档 3.4 / 3.6 / 3.7 节）
INPUT_SHAPE = (N_FRAMES, N_FEATURES, 1)
NUM_CLASSES = 2
CLASS_NAMES = ["cough", "non_cough"]
CNN_FILTERS = (32, 64)
KERNEL_SIZE = (3, 3)
POOL_SIZE = (2, 2)
LSTM_UNITS = (64, 32)
DENSE_UNITS = 64
DROPOUT_RATE = 0.3
LEARNING_RATE = 0.001
BATCH_SIZE = 32
EPOCHS = 150
EARLY_STOPPING_PATIENCE = 20
REDUCE_LR_PATIENCE = 8
USE_CLASS_WEIGHT = True
CV_FOLDS = 5

# 推理 / 长音频监测 / 预警参数（设计文档 3.6 / 3.8 节）
WINDOW_SEC = 1.5
HOP_SEC = 0.5
CONFIDENCE_THRESHOLD = 0.4   # 监测判定阈值（0.5->0.4 提高召回，实测误报不增）
COOLDOWN_SEC = 2.0
ALERT_COUGH_PER_HOUR = 10
ALERT_RATIO_BASELINE = 1.5

SEED = 42

# ===========================================================================
# 监测服务 / API（生产级）
# ===========================================================================
LOG_DIR = ROOT_DIR / "logs"                          # 滚动日志目录
UPLOAD_DIR = DATA_DIR / "uploads"                    # API 上传临时目录
MONITOR_WATCH_DIR = DATA_DIR / "monitor_in"          # 采集端落盘目录
MONITOR_ARCHIVE_DIR = DATA_DIR / "monitor_done"      # 处理完归档目录（可选）
MONITOR_INTERVAL_SEC = 10.0                          # 轮询间隔（秒）
MONITOR_FARM_CODE = "net01"                          # 猪场/栋舍编号
MONITOR_DEVICE_ID = "dev-001"                        # 设备编号
MONITOR_WINDOW_MINUTES = 60                          # 统计窗口（分钟）
MONITOR_WRITE_STATUS_EVERY_SEC = 60                  # 状态落库周期（秒）
MONITOR_HEARTBEAT_SEC = 30                           # 心跳周期（秒）
MONITOR_MODEL_VERSION = "cnn_bilstm_v1"              # 模型版本号
API_HOST = "0.0.0.0"
API_PORT = 5000
# 非空则开启 Bearer Token 鉴权；生产环境在 .env 中设置强随机串
API_TOKEN = os.environ.get("MONITOR_API_TOKEN", "")
