@echo off
REM MISRA GenAI System — Quick launcher
REM Double-click this file to start the web UI

title MISRA GenAI System
cd /d %~dp0

echo.
echo ============================================================
echo   MISRA GenAI System
echo ============================================================
echo.
echo  Starting Flask web server...
echo  Open http://127.0.0.1:5000 in your browser
echo.
echo  Make sure llama-server is running first:
echo    C:\Users\sanjay.ravichander\llama_cpp\llama-server.exe ^
echo      -m C:\models\Mistral-7B-Instruct-v0.3-Q4_K_M.gguf ^
echo      --host 127.0.0.1 --port 8080 --ctx-size 4096 --threads 4
echo.
echo ============================================================

call venv310\Scripts\activate.bat
python app\web\server.py

pause
