@echo off
rem This top-level cd command is still good practice.
cd /d "%~dp0"

echo =================================================================
echo  Launching the Waitress Server as 'JeaToolUser'
echo  ALL OUTPUT AND ERRORS WILL BE SAVED TO 'server_logs.txt'
echo =================================================================

set LOGFILE=server_logs.txt
if exist %LOGFILE% del %LOGFILE%

rem This is the final, robust command.
rem It tells the new cmd process to first change to the project directory (%~dp0),
rem and THEN execute the python script. This guarantees the paths are correct.
runas /user:JeaToolUser "cmd /c (cd /d ""%~dp0"" & .\venv\Scripts\python.exe run_waitress.py > %LOGFILE% 2>&1)"

echo.
echo Launch command has been sent. The 'server_logs.txt' file should now be created.
echo Please check it for startup messages or errors.
echo.
pause