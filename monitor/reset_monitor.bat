@echo off
REM ============================================================
REM  Reset monitor tables (dedup/events) - used when you retrain
REM  the model and want to re-run ALL old audio with new model.
REM  Normal incremental monitoring does NOT need this.
REM ============================================================
cd /d "%~dp0.."
set "PY=python"

set /p c=This will DELETE processed_audio/cough_event/monitor_status/heartbeat. Continue? (y/n):
if /i not "%c%"=="y" (echo cancelled. & pause & exit /b 0)

"%PY%" monitor\scripts\12_reset_monitor.py --all
echo.
echo Now run monitor\run_full_pipeline.bat to re-process all audio.
pause
