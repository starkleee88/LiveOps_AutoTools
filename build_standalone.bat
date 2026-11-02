@echo off
cd /d "%~dp0"
echo [INFO] Dang build Standalone Event Tool...
if exist ".venv\Scripts\pyinstaller.exe" (
    .venv\Scripts\pyinstaller --noconfirm --clean standalone_tool.spec
) else (
    pyinstaller --noconfirm --clean standalone_tool.spec
)
echo ----------------------------------------------------
if %ERRORLEVEL% equ 0 (
    echo [OK] Build thanh cong: dist\standalone_tool.exe
) else (
    echo [ERR] Build that bai!
)
pause
