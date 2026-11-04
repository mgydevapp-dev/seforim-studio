@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem Start Seforim Studio from the source files. Installs any missing add-ons first (needs internet only that once).
where py >nul 2>nul || (echo Python is not installed. Use the portable SeforimStudio.exe instead, or install Python from python.org. & pause & exit /b 1)
py -c "import cv2, numpy, PIL, docx, pypdfium2, pyluach" >nul 2>nul
if errorlevel 1 (
  echo Installing the add-ons Seforim Studio needs ^(one time^)...
  py -m pip install -r requirements.txt || (echo Could not install. Check the internet connection. & pause & exit /b 1)
)
start "" pyw SeforimStudio.py
