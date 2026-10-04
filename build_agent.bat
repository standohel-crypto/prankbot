@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo Python 3.12+ not found.
  pause
  exit /b 1
)

python -m pip install -r agent\requirements.txt
if errorlevel 1 goto :error

python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --name PrankBotAgent ^
  --paths agent ^
  agent\agent.py
if errorlevel 1 goto :error

set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"

if not defined ISCC (
  echo EXE ready: dist\PrankBotAgent.exe
  pause
  exit /b 0
)

"%ISCC%" installer\AgentSetup.iss
if errorlevel 1 goto :error

echo Installer ready: output\PrankBotAgentSetup.exe
start "" output
pause
exit /b 0

:error
echo Build failed.
pause
exit /b 1
