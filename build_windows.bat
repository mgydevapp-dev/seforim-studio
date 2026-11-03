@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === Building SeforimStudio.exe (Step 4) ===
py -m pip install pyinstaller
py -m PyInstaller SeforimStudio.spec --noconfirm || (echo Build failed & pause & exit /b 1)
echo.
echo Finished: dist\SeforimStudio\SeforimStudio.exe
echo Copy the whole dist\SeforimStudio folder to where you want it (e.g. Documents) and double-click SeforimStudio.exe.
echo Your library and notes are kept in the "data" folder next to the .exe.
pause
