@echo off
chcp 65001 >nul
echo === Seforim Studio: one-time setup (needs internet only now) ===
where py >nul 2>nul || (echo Python is not installed. Get it from https://www.python.org/downloads/ and tick "Add python.exe to PATH". & pause & exit /b 1)
py -m pip install --upgrade pip
py -m pip install -r requirements.txt || (echo Package install failed. & pause & exit /b 1)
echo.
echo Done. Double-click run_windows.bat to start Seforim Studio.
echo Optional: build a double-click .exe with build_windows.bat
pause
