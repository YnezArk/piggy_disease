# 数据目录

```
data/
├─ raw/
│  ├─ six_class/     # 辨病 6 类，540 条
│  │  ├─ normal/ 167
│  │  ├─ influenza/ 135
│  │  ├─ mycoplasma/ 148
│  │  ├─ app/ 49
│  │  ├─ prrs/ 28
│  │  └─ other_disease/ 13
│  └─ monitor/       # 监测二分类，540 条（359 咳嗽 / 181 非咳嗽）
├─ features/
│  ├─ monitor/       # features.npz + dataset_split.npz（39 维）
│  └─ diagnosis/     # features_{train,val,test}.npz（84 维）+ 142 维扩展
├─ knowledge/
│  ├─ kg/            # 辨证库 symptom_disease.csv、论治库 disease_formula.csv
│  └─ rag/classics/  # 典籍库 txt
├─ sql/              # pig_diag_v2.sql、pig_cough_dataset.sql
└─ samples/          # 演示音频
```

- 原始音频不要手工改名：`diagnosis/features.py` 与 `monitor/src/dataset.py` 按目录名取标签。
- `data/features` 已包含提取结果，可直接训练；重新提取会覆盖同名 npz。
- 大文件建议用 Git LFS；`.gitignore` 已预留说明。
