@echo off
setlocal
set "ROOT=%~dp0"
set "PY=%ROOT%.venv\Scripts\python.exe"
set "PYINSTALLER=%ROOT%.venv\Scripts\pyinstaller.exe"
set "PYTHONPATH=%ROOT%src;%PYTHONPATH%"

if not exist "%PY%" (
  echo [ERROR] Virtual environment not found: %ROOT%.venv
  echo Create it and install dependencies from pyproject.toml.
  exit /b 1
)

if /I "%~1"=="app" goto app
if /I "%~1"=="test" goto test
if /I "%~1"=="build" goto build

echo Usage: run ^<app^|test^|build^>
exit /b 2

:app
"%PY%" -m dfa_app
exit /b %ERRORLEVEL%

:test
set "QT_QPA_PLATFORM=offscreen"
"%PY%" -m pytest "%ROOT%tests\test_dfa_minimization.py"
exit /b %ERRORLEVEL%

:build
if not exist "%PYINSTALLER%" (
  echo [ERROR] PyInstaller not found in .venv.
  exit /b 1
)
"%PYINSTALLER%" --clean --noconfirm --distpath "%ROOT%release" "%ROOT%dfa-app.spec"
if errorlevel 1 exit /b %ERRORLEVEL%
echo.
echo Ready: %ROOT%release\DFA-Minimizer.exe
exit /b 0
