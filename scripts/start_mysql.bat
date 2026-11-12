@echo off
rem Starts the project's own MySQL 8 on port 3307 (skips if already running).
netstat -ano | findstr ":3307 " | findstr LISTENING >nul && (echo MySQL 8 already running & exit /b 0)
start "MySQL8-BreakingPoint" /min "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqld.exe" --defaults-file="%~dp0my8.ini" --console
ping -n 9 127.0.0.1 >nul
