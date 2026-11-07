@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
if not exist ".venv\Scripts\python.exe" goto setup
:run
".venv\Scripts\python.exe" -X utf8 "%~dp0main.py" %*
set "GAME_EXIT=%ERRORLEVEL%"
if not "%GAME_EXIT%"=="0" pause
exit /b %GAME_EXIT%
:setup
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
if errorlevel 1 goto setup_error
goto run
:setup_error
echo Python environment setup failed. Please check the error above.
pause
exit /b 1
