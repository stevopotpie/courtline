@echo off
rem Pull NBA odds once and push to GitHub. Double-click to run by hand; Task Scheduler passes "auto".
cd /d "%~dp0"
set PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe
if not exist "%PY%" set PY=python
echo %date% %time% start NBA pull >> run_log.txt
"%PY%" fetch_nba_odds.py >> run_log.txt 2>&1
echo %date% %time% end NBA pull (exit %errorlevel%) >> run_log.txt
if /i not "%1"=="auto" (type logs\nba_odds_log.txt | more & pause)
