@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo  Seforim Studio - build a portable SeforimStudio.exe
echo  Run this ONCE on a Windows PC that has internet.
echo  Result: folder "SeforimStudio-Portable" to copy to any
echo          offline computer (USB stick). Nothing to install.
echo ============================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_portable.ps1"
echo.
pause
