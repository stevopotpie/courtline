@echo off
rem One NBA odds pull a day at 6:15 PM (about 90 credits a month), close to the 7 PM ET tips.
cd /d "%~dp0"
schtasks /Create /F /SC DAILY /ST 18:15 /TN "Courtline NBA odds" /TR "\"%~dp0run_nba_odds.bat\" auto"
echo Scheduled "Courtline NBA odds" daily at 6:15 PM. Check it in Task Scheduler.
pause
