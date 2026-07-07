@echo off
setlocal
set "LOCAL_RUNNER=%CD%\run.cmd"

if exist "%LOCAL_RUNNER%" (
  call "%LOCAL_RUNNER%" %*
  exit /b %ERRORLEVEL%
)

echo [ERROR] run.cmd was not found in the current directory: %CD%
exit /b 1

