@echo off
rem Starts the project's own MySQL 8 on port 3307 (skips if already running).
rem The data folder is <project>\mysql-data, worked out from where this file lives.
netstat -ano | findstr ":3307 " | findstr LISTENING >nul && (echo MySQL 8 already running & exit /b 0)
set "PROJ=%~dp0.."
for %%I in ("%PROJ%") do set "PROJ=%%~fI"
set "BASE=C:\Program Files\MySQL\MySQL Server 8.4"
start "MySQL8-BreakingPoint" /min "%BASE%\bin\mysqld.exe" --defaults-file="%~dp0my8.ini" --basedir="%BASE%" --datadir="%PROJ%\mysql-data" --console
ping -n 9 127.0.0.1 >nul
