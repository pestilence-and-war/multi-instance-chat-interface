@echo off
rem This top-level cd command is still good practice.
cd /d "%~dp0"

echo =================================================================
echo  Launching the Waitress Server as 'JeaToolUser'
echo  ALL OUTPUT AND ERRORS WILL BE SAVED TO 'server_logs.txt'
echo =================================================================

set SERVER_LOGFILE=server_logs.txt
if exist %SERVER_LOGFILE% del %SERVER_LOGFILE%

rem This is the final, robust command.
rem It tells the new cmd process to first change to the project directory (%~dp0),
rem and THEN execute the python script. This guarantees the paths are correct.
start "AATFS_WebApp" runas /user:JeaToolUser "cmd /c (cd /d ""%~dp0"" & .\venv\Scripts\python.exe run_waitress.py > %SERVER_LOGFILE% 2>&1)"

set MONITOR_LOGFILE=monitor_logs.txt
if exist %MONITOR_LOGFILE% del %MONITOR_LOGFILE%

echo --- Launching the Event Monitor (logs in %MONITOR_LOGFILE%) ---
start "AATFS_Monitor" cmd /c (cd /d ""%~dp0"" & runas /user:JeaToolUser "cmd /c (cd /d \"\"%~dp0\"\" & .\venv\Scripts\python.exe event_monitor.py > %MONITOR_LOGFILE% 2>&1)")

echo.
echo AATFS launch commands sent.
echo WebApp UI will be available at http://localhost:5000
echo Check log files for real-time status.
echo.
pause