@echo off
cd /d "%~dp0"
setlocal enabledelayedexpansion

:: Check if a file was dragged and dropped
if "%~1" neq "" (
    set "FILE_TO_BUILD=%~1"
) else (
    set /p "FILE_TO_BUILD=Nhap ten file Python can dong goi (vi du: main.py): "
)

:: Remove quotes if any
set "FILE_TO_BUILD=!FILE_TO_BUILD:"=!"

if not exist "!FILE_TO_BUILD!" (
    echo [Loi] File "!FILE_TO_BUILD!" khong ton tai.
    pause
    exit /b
)

:: Get filename without extension
for %%F in ("!FILE_TO_BUILD!") do (
    set "FILE_NAME=%%~nF"
)

echo ----------------------------------------------------
echo [INFO] Dang dong goi: !FILE_TO_BUILD!
echo [INFO] Ten file dau ra: !FILE_NAME!.exe
echo [INFO] Che do: An console --windowed
echo ----------------------------------------------------

:: Check if virtual environment has PyInstaller
if exist ".venv\Scripts\pyinstaller.exe" (
    echo [INFO] Su dung PyInstaller tu virtual environment .venv...
    .venv\Scripts\pyinstaller --noconfirm --onefile --windowed "!FILE_TO_BUILD!"
) else (
    echo [INFO] Khong tim thay .venv. Thu chay bang pyinstaller he thong...
    pyinstaller --noconfirm --onefile --windowed "!FILE_TO_BUILD!"
)

if %ERRORLEVEL% equ 0 (
    echo ----------------------------------------------------
    echo [OK] Dong goi thanh cong!
    echo [OK] File exe da duoc luu tai: %CD%\dist\!FILE_NAME!.exe
    echo ----------------------------------------------------
) else (
    echo ----------------------------------------------------
    echo [ERR] Co loi xay ra trong qua trinh dong goi.
    echo ----------------------------------------------------
)

pause
