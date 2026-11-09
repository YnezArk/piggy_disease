@echo off
REM ============================================================
REM  Pig Cough Monitor - ONE-CLICK TEST
REM  Detect audio in data\raw\six_class, then show monitor stats.
REM  Results are written to MySQL when it is reachable.
REM ============================================================
cd /d "%~dp0.."
set "PY=python"

echo.
echo ===== [1/2] detect audio (saved to MySQL when available) =====
"%PY%" monitor\scripts\07_monitor_service.py --batch-dir data\raw\six_class --farm-code net01

echo.
echo ===== [2/2] monitoring stats ^& recent events =====
"%PY%" monitor\scripts\09_monitor_stats.py --farm net01 --hours 24

echo.
echo ===== DONE. press any key to close =====
pause
