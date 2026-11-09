# -*- coding: utf-8 -*-
"""
10_build_retrain_dataset.py —— 用 data/raw/six_class 构建重训数据集
把带病种标签的音频按类别复制到 data/raw/cough 和 data/raw/non_cough（扁平），
保留原 data/raw 里的 200 个样本，一起用于重新训练。

标签规则（可改下面的映射）：
  咳嗽(正样本)  : contagious_pleuropneumonia(app) / mycoplasma(myco) / prrs / swine_influenza(flu_*)
  非咳嗽(负样本): normal/**(environment/hungry/oink/play/scream/snore/unknown_normal)
                  unknown/**、swine_influenza/gander/**(鹅鸣，非猪咳嗽)
  跳过          : *.aup3（Audition 工程文件）

运行：python scripts\10_build_retrain_dataset.py [--src 数据根目录]
"""
import sys
import shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse

import config

# 顶层目录 -> (标签, 前缀)。gander 单独处理（鹅鸣 -> 非咳嗽）
COUGH_DIRS = {
    "contagious_pleuropneumonia": "app_",
    "mycoplasma": "myco_",
    "prrs": "prrs_",
    "swine_influenza": "flu_",     # 只取该目录直接下的 flu_*.wav；gander 子目录按非咳嗽处理
}
NON_COUGH_DIRS = {
    "normal": "norm_",
    "unknown": "unk_",
}
NON_COUGH_SUBDIRS = {             # 非咳嗽目录下的子目录（如 normal/scream、swine_influenza/gander）
    "scream": "scream_",
    "snore": "snore_",
    "oink": "oink_",
    "hungry": "hungry_",
    "play": "play_",
    "environment": "env_",
    "unknown_normal": "unorm_",
    "gander": "gander_",
}

# other_disease 目录：rhinobyon_*(鼻炎)=咳嗽，unknown_*=非咳嗽
OTHER_DISEASE_DIR = "other_disease"
OTHER_COUGH_PREFIX = "rhino_"    # rhinobyon_*.wav -> data/raw/cough
OTHER_NON_PREFIX = "unk_"        # unknown_*.wav   -> data/raw/non_cough
EXT = {".wav", ".mp3", ".flac", ".ogg"}


def copy_files(src_files, dst_dir, prefix):
    dst_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in src_files:
        try:
            # 源文件名若已带相同前缀则不再重复加
            fname = f.name if f.name.startswith(prefix) else (prefix + f.name)
            shutil.copy2(str(f), str(dst_dir / fname))
            n += 1
        except Exception as e:
            print(f"  [warn] 复制失败 {f.name}: {e}")
    return n


def main(args):
    src = Path(args.src)
    if not src.exists():
        print(f"源目录不存在: {src}")
        return

    cough_dir = config.RAW_DIR / "cough"
    non_dir = config.RAW_DIR / "non_cough"
    n_cough = n_non = 0

    # 正样本（病种顶层目录直接下的文件）
    for top, prefix in COUGH_DIRS.items():
        files = [f for f in (src / top).glob("*") if f.is_file() and f.suffix.lower() in EXT]
        n_cough += copy_files(files, cough_dir, prefix)
        print(f"[cough] {top}: {len(files)} 个")

    # 负样本：normal/**、unknown/** 下的所有文件（含子目录）
    for top, prefix in NON_COUGH_DIRS.items():
        files = [f for f in (src / top).rglob("*") if f.is_file() and f.suffix.lower() in EXT]
        n_non += copy_files(files, non_dir, prefix)
        print(f"[non]   {top}/**: {len(files)} 个")

    # 负样本：swine_influenza/gander/**（鹅鸣）
    gander_files = [f for f in (src / "swine_influenza" / "gander").rglob("*")
                    if f.is_file() and f.suffix.lower() in EXT]
    n_non += copy_files(gander_files, non_dir, "gander_")
    print(f"[non]   swine_influenza/gander/**: {len(gander_files)} 个（鹅鸣按非咳嗽处理，如需改请编辑本脚本）")

    # other_disease：rhinobyon_*(鼻炎)=咳嗽，unknown_*=非咳嗽
    od = src / OTHER_DISEASE_DIR
    if od.exists():
        rhino = [f for f in od.glob("rhinobyon_*.wav")]
        n_cough += copy_files(rhino, cough_dir, OTHER_COUGH_PREFIX)
        print(f"[cough] other_disease/rhinobyon_*: {len(rhino)} 个")
        unk = [f for f in od.glob("unknown_*.wav")]
        n_non += copy_files(unk, non_dir, OTHER_NON_PREFIX)
        print(f"[non]   other_disease/unknown_*: {len(unk)} 个")

    # 原数据统计
    orig_cough = len(list(cough_dir.glob("*.wav")))
    orig_non = len(list(non_dir.glob("*.wav")))
    print("\n===== 数据集汇总 =====")
    print(f"data/raw/cough:     {orig_cough} 个（含本次新增 {n_cough}）")
    print(f"data/raw/non_cough: {orig_non} 个（含本次新增 {n_non}）")
    print("下一步：python scripts\\01_preprocess_audio.py --no-db -> 02 -> 03 -> 04 -> 05")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(config.DATA_DIR / "raw" / "six_class"))
    main(ap.parse_args())