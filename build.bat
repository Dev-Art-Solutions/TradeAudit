@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo =======================================================
echo          TradeAudit Windows EXE Build
echo =======================================================

if not exist ".venv_build\Scripts\python.exe" (
    echo [1/6] Creating build virtual environment .venv_build ...
    py -3.12 -m venv .venv_build
    if !ERRORLEVEL! neq 0 (
        py -3 -m venv .venv_build
    )
    if !ERRORLEVEL! neq 0 (
        echo [ERROR] Could not create a virtual environment. Is Python 3.11+ installed and on PATH?
        exit /b 1
    )
) else (
    echo [1/6] Reusing existing .venv_build ...
)

set PY=.venv_build\Scripts\python.exe

echo [2/6] Installing dependencies ^(this can take a few minutes the first time^) ...
"%PY%" -m pip install --quiet --upgrade pip
"%PY%" -m pip install --quiet -r requirements.txt
"%PY%" -m pip install --quiet -e ".[dev,build]"
if !ERRORLEVEL! neq 0 (
    echo [ERROR] Dependency installation failed.
    exit /b 1
)

echo [3/6] Running automated test suite ...
set QT_QPA_PLATFORM=offscreen
"%PY%" -m pytest -q
if !ERRORLEVEL! neq 0 (
    echo [ERROR] Test suite failed! Aborting packaging.
    exit /b 1
)
echo [SUCCESS] All tests passed.

echo [4/6] Generating application icon assets ...
"%PY%" scripts\generate_icons.py
if !ERRORLEVEL! neq 0 (
    echo [WARNING] Icon generation failed, proceeding with existing assets.
)

echo [5/6] Packaging Windows executable with PyInstaller ...
"%PY%" -m PyInstaller --clean --noconfirm TradeAudit.spec
if !ERRORLEVEL! neq 0 (
    echo [ERROR] PyInstaller packaging failed!
    exit /b 1
)

echo [6/6] Verifying build output ...
if exist "dist\TradeAudit\TradeAudit.exe" (
    echo =======================================================
    echo  BUILD SUCCESSFUL: dist\TradeAudit\TradeAudit.exe
    echo =======================================================
) else (
    echo [ERROR] Executable dist\TradeAudit\TradeAudit.exe was not created!
    exit /b 1
)

endlocal
