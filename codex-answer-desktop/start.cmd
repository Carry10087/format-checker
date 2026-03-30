@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT_DIR=%~dp0"
for %%I in ("%ROOT_DIR%..") do set "WORKSPACE_DIR=%%~fI"

set "BACKEND_DIR=%ROOT_DIR%backend"
set "DESKTOP_DIR=%ROOT_DIR%desktop"
set "BACKEND_REQ=%BACKEND_DIR%\requirements.txt"
set "VENV_DIR=%BACKEND_DIR%\.venv"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
set "LOCAL_CONFIG=%ROOT_DIR%start.local.cmd"
set "WORKSPACE_SKILL=%WORKSPACE_DIR%\answer-format-rules\SKILL.md"
set "USER_SKILL=%USERPROFILE%\.codex\skills\strict-answer-formatter\SKILL.md"

cd /d "%ROOT_DIR%"

if exist "%LOCAL_CONFIG%" (
  call "%LOCAL_CONFIG%"
)

if not exist "%VENV_PYTHON%" (
  echo [INFO] Creating backend virtual environment...
  py -3 -m venv "%VENV_DIR%" 2>nul
  if not exist "%VENV_PYTHON%" (
    python -m venv "%VENV_DIR%"
  )
  if errorlevel 1 (
    echo [ERROR] Failed to create backend virtual environment.
    pause
    exit /b 1
  )

  echo [INFO] Installing backend dependencies...
  "%VENV_PYTHON%" -m pip install -r "%BACKEND_REQ%"
  if errorlevel 1 (
    echo [ERROR] Failed to install backend dependencies.
    pause
    exit /b 1
  )
)

if not exist "%DESKTOP_DIR%\node_modules\electron" (
  echo [INFO] Installing desktop dependencies...
  set "ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/"
  pushd "%DESKTOP_DIR%"
  call npm.cmd install
  set "NPM_EXIT=!errorlevel!"
  popd
  if not "!NPM_EXIT!"=="0" (
    echo [ERROR] Failed to install desktop dependencies.
    pause
    exit /b !NPM_EXIT!
  )
)

if not defined CODEX_DESKTOP_PYTHON set "CODEX_DESKTOP_PYTHON=%VENV_PYTHON%"
if not defined CODEX_DESKTOP_BACKEND_PORT set "CODEX_DESKTOP_BACKEND_PORT=8765"
if not defined CODEX_AGENT_API_URL set "CODEX_AGENT_API_URL=http://127.0.0.1:9000/v1/chat/completions"
if not defined CODEX_AGENT_MODEL set "CODEX_AGENT_MODEL=gpt-5.2"

if not defined CODEX_SKILL_PATH (
  if exist "%WORKSPACE_SKILL%" (
    set "CODEX_SKILL_PATH=%WORKSPACE_SKILL%"
  ) else if exist "%USER_SKILL%" (
    set "CODEX_SKILL_PATH=%USER_SKILL%"
  )
)

echo [INFO] Starting Codex Answer Desktop...
echo [INFO] Backend Python: %CODEX_DESKTOP_PYTHON%
echo [INFO] Backend port: %CODEX_DESKTOP_BACKEND_PORT%
echo [INFO] Model endpoint: %CODEX_AGENT_API_URL%
echo [INFO] Model name: %CODEX_AGENT_MODEL%

if defined CODEX_SKILL_PATH (
  if exist "%CODEX_SKILL_PATH%" (
    echo [INFO] Skill file: %CODEX_SKILL_PATH%
  ) else (
    echo [WARN] CODEX_SKILL_PATH points to a missing file: %CODEX_SKILL_PATH%
  )
) else (
  echo [WARN] No skill file configured. Runs may fail until CODEX_SKILL_PATH is set.
)

if not defined CODEX_AGENT_API_KEY (
  echo [WARN] CODEX_AGENT_API_KEY is not set. This is fine if your endpoint does not require auth.
)

pushd "%DESKTOP_DIR%"
call npm.cmd start
set "APP_EXIT=!errorlevel!"
popd

if not "!APP_EXIT!"=="0" (
  echo.
  echo [ERROR] Desktop app exited with code !APP_EXIT!.
  pause
  exit /b !APP_EXIT!
)

endlocal
