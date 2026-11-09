@echo off
REM ============================================================
REM  Pig Cough Monitor - FULL TRAINING PIPELINE
REM  [1] preprocess -> [2] features -> [3] split -> [4] train
REM  -> [5] evaluate -> [6] batch detect -> [7] stats
REM ============================================================
cd /d "%~dp0.."
set "PY=python"

echo.
echo ===== [1/7] preprocess audio =====
"%PY%" monitor\scripts\01_preprocess_audio.py

echo.
echo ===== [2/7] extract MFCC features =====
"%PY%" monitor\scripts\02_extract_features.py

echo.
echo ===== [3/7] build dataset 8:1:1 =====
"%PY%" monitor\scripts\03_build_dataset.py

echo.
echo ===== [4/7] train CNN-BiLSTM =====
"%PY%" monitor\scripts\04_train.py

echo.
echo ===== [5/7] evaluate test set =====
"%PY%" monitor\scripts\05_evaluate.py

echo.
echo ===== [6/7] batch detect =====
"%PY%" monitor\scripts\07_monitor_service.py --batch-dir data\raw\six_class --farm-code net01

echo.
echo ===== [7/7] monitoring stats =====
"%PY%" monitor\scripts\09_monitor_stats.py --farm net01

echo.
echo ===== DONE. model in models\monitor\best_model.h5. press any key to close =====
pause
