# 音识咳 · 猪咳嗽声智能监测与诊疗辅助决策系统

三个可独立运行、通过契约解耦的模块（监测 / 辨病 / 论治）：

| 模块 | 任务 | 输入 → 输出 | 核心方法 |
|---|---|---|---|
| `monitor/` | 咳嗽事件监测 | 长音频 → 咳嗽时间戳/频次/预警 | 39 维 MFCC+Δ+Δ²，CNN-BiLSTM 二分类，滑窗检测 |
| `diagnosis/` | 辨病（声学分类） | 1 s 咳嗽音频 → 疾病类别 + 置信度 | 84 维多域特征，SSLRB（SVM-Stacking + LR 集成） |
| `prescription/` | 辨证论治 | 疾病 + 症状/体温/体重 → 证型、方剂、安全校验 | RAG 三库检索 + Qwen 三阶段生成 + 规则校验 |

`diagnosis` 与 `prescription` 通过 `diagnosis/bridge.py` 的契约串联；`monitor` 独立运行，输出可供下游使用。

---

## 目录结构

```
音识咳/
├─ monitor/                    # 监测模块（原 pig-cup）
│  ├─ config.py                # 全部路径/参数集中配置
│  ├─ src/                     # 预处理、特征、模型、推理、监测、API
│  ├─ scripts/                 # 00~17 分步脚本
│  ├─ notebooks/               # 流程演示 notebook
│  └─ run_*.bat                # Windows 一键脚本
├─ diagnosis/                  # 辨病模块（原 辨病）
│  ├─ bianbing_config.py       # 路径/数据库配置
│  ├─ features.py              # 84 维特征 + 数据划分
│  ├─ train_sslr.py            # SSLRB 训练
│  ├─ train_baseline.py        # SVM 基线
│  ├─ predict.py               # 单条音频推理
│  ├─ bridge.py                # 辨病 → 论治契约
│  └─ batch_test.py            # 批量测试
├─ prescription/               # 诊疗决策模块（原 决策）
│  ├─ therapy_engine.py        # 三阶段编排
│  ├─ rag_retrieve.py          # 三库内存检索
│  ├─ kb_lookup.py / safety.py # 知识库查询、剂量与配伍校验
│  ├─ api_server.py            # FastAPI 服务
│  ├─ pipeline.py              # 辨病 + 论治一键串联
│  └─ interactive_demo.py      # 终端交互演示（流式输出）
├─ data/
│  ├─ raw/six_class/           # 540 条六类音频（辨病）
│  ├─ raw/monitor/             # 540 条二分类音频（监测）
│  ├─ features/                # 提取好的 npz（monitor / diagnosis）
│  ├─ knowledge/{kg,rag}/      # 辨证库、论治库、典籍库
│  ├─ sql/                     # 两个 MySQL 库的建库脚本
│  └─ samples/                 # 演示音频
├─ models/{monitor,diagnosis}/ # 已训练模型
├─ results/{monitor,diagnosis}/# 评估图表、实验报告
├─ docs/                       # 01~04 核心文档 + 项目/文献原始材料
├─ deploy/monitor/             # 监测模块 Docker 部署包
├─ tests/                      # 手动测试与网关连通性测试
└─ requirements/               # 按模块拆分依赖
```

> `_archive/` 是整理时隔离出的重复/派生文件（旧文档、旧虚拟环境、Audacity 工程、monitor_in 重复数据、旧 SQL 等），确认无误后可整体删除。

---

## 快速开始

```bash
# 1. 环境（建议 Python 3.10+）
python -m pip install -r requirements/base.txt
python -m pip install -r requirements/prescription.txt   # 论治/API
python -m pip install -r requirements/monitor.txt        # 监测（含 TensorFlow）

# 2. 配置
cp .env.example .env        # 填写大模型 Key 与 MySQL 密码

# 3. 演示
python diagnosis/predict.py data/raw/six_class/mycoplasma/myco_1.wav
python prescription/interactive_demo.py
python prescription/pipeline.py data/raw/six_class/app/app_1.wav --temp 40.1
python monitor/scripts/07_monitor_service.py --file data/raw/monitor/cough/app_1.wav
```

### 数据库

- `data/sql/pig_diag_v2.sql` → 诊疗库 `pig_diag_v2`（辨病 + 论治 + 安全规则）
- `data/sql/pig_cough_dataset.sql` → 监测库 `pig_cough_dataset`（事件、预警、样本）

导入后按 `.env.example` 配置连接。监测模块连不上数据库时会自动回退本地目录扫描。

### API

```bash
# 诊疗决策（FastAPI，端口 8000）
cd prescription && python api_server.py
# 或：python -m uvicorn api_server:app --app-dir prescription --port 8000

# 监测（Flask，端口 5000）
python monitor/scripts/08_api_server.py
```

---

## 数据说明

| 数据集 | 规模 | 类别 | 用途 |
|---|---|---|---|
| `data/raw/six_class` | 540 | normal 167 / influenza 135 / mycoplasma 148 / app 49 / prrs 28 / other_disease 13 | 辨病训练与评估（8:1:1，seed=42） |
| `data/raw/monitor` | 540（359 咳嗽 / 181 非咳嗽） | cough / non_cough | 监测二分类训练 |
| `data/features/*` | — | — | 已提取特征，可直接训练，无需重新跑特征 |

两套音频内容有交集但划分口径不同：六类用于“辨病”，二分类用于“咳嗽事件检测”，不要混用指标。

---

## 关键口径

- 辨病独立测试集：**Macro-F1 0.7516 / 准确率 0.833 / 健康召回 0.941**（54 条，seed=42）。
- 辨病 5 折交叉验证：**SSLRB 0.726±0.032；SVM 基线 0.761±0.043**（train+val 486 条）。
- 监测模型为 39 维 MFCC 输入的 CNN-BiLSTM：片段级留出 Acc 96.61%；文件级严格留出 Acc 92.59% / F1 0.944；全量回测 98.15%（in-sample）。
- 论治 3 次 LLM 调用（查询改写/辨证/组方）+ 1 次规则校验；关闭思考模式后端到端约 30 s。

---

## 文档

- `docs/01_系统总览.md`：架构、数据、指标口径总表、答辩 10 问
- `docs/02_监测模块.md`：预处理、特征、模型、调参、指标、部署
- `docs/03_辨病与论治.md`：84 维特征、SSLRB、RAG 三库、安全规则、数据库
- `docs/04_运行测试与部署.md`：环境、命令、API、测试、故障排查
- `docs/项目/`：项目方案、校赛技术 PPT、项目安排
- `docs/文献/`：参考文献 PDF

> 旧版分散文档在 `_archive/docs_old/`，确认后可删除。文档中的 `E:\pig-cup`、`辨病/`、`决策/` 等为历史路径。
