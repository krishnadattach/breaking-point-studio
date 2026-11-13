@echo off
rem One click: starts MySQL 8, the backend (port 8000) and the dashboard (port 5173), then opens the browser.
rem Free test mode (no Claude/Tavily cost):  start.bat mock
setlocal
set ROOT=%~dp0
cd /d "%ROOT%"

set MODE=
if /i "%~1"=="mock" set MODE=set MOCK_LLM=1^&^& set MOCK_SEARCH=1^&^&

echo [1/3] Starting MySQL 8 ...
call "%ROOT%scripts\start_mysql.bat"

echo [2/3] Starting backend on http://localhost:8000 ...
start "BP backend" /d "%ROOT%backend" cmd /k "%MODE% "%ROOT%.venv\Scripts\python.exe" -m uvicorn bp.api:app --port 8000"

echo [3/3] Starting dashboard on http://localhost:5173 ...
if not exist "%ROOT%frontend\node_modules" (
  echo First run: installing dashboard packages ...
  pushd "%ROOT%frontend" & call npm install & popd
)
start "BP dashboard" /d "%ROOT%frontend" cmd /k "npm run dev"

ping -n 6 127.0.0.1 >nul
start "" http://localhost:5173
echo.
echo Running. Close the two "BP" windows to stop. (MySQL keeps running in its own minimized window.)
endlocal
