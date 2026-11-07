@echo off
chcp 65001 >nul
where code >nul 2>&1
if errorlevel 1 (
    start "" "%~dp0용병일기.code-workspace"
) else (
    code "%~dp0용병일기.code-workspace"
)
