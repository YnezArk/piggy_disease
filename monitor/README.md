# 监测模块（CNN-BiLSTM）

原始音频 → 预处理 → 39 维 MFCC(+Δ+Δ²) → CNN-BiLSTM 二分类 → 长音频滑窗检测 → 频次统计与预警。

## 快速开始

```bash
# 在项目根目录执行
python -m pip install -r requirements/monitor.txt

# 单文件检测（已训练模型）
python monitor/scripts/07_monitor_service.py --file data/raw/monitor/cough/app_1.wav

# 批量检测
python monitor/scripts/07_monitor_service.py --batch-dir data/raw/six_class --farm-code net01

# 启动 API（Flask，5000 端口）
python monitor/scripts/08_api_server.py
```

Windows 一键脚本在 `monitor/` 下：`run_full_pipeline.bat`、`run_training.bat`、`reset_monitor.bat`。

## 完整训练流水线

```bash
python monitor/scripts/01_preprocess_audio.py --no-db
python monitor/scripts/02_extract_features.py
python monitor/scripts/03_build_dataset.py
python monitor/scripts/04_train.py --cv
python monitor/scripts/05_evaluate.py
```

## 目录

```
monitor/
├─ config.py        # 路径、音频/特征/训练/预警参数、数据库
├─ src/             # audio_io / preprocess / features / model / train / inference / monitor / api
├─ scripts/         # 00~17 分步脚本
├─ notebooks/       # 流程演示
└─ run_*.bat
```

数据与模型位于项目根目录：`data/raw/monitor/`、`data/features/monitor/`、`models/monitor/`、`results/monitor/`。
详细设计、调参、部署与 API 文档见 `docs/监测/`。
