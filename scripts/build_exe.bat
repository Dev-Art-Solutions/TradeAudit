@echo off
setlocal enabledelayedexpansion

echo =======================================================
echo          TradeAudit Production Build Pipeline
echo =======================================================

echo [1/4] Running automated test suite...
pytest tests\unit
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Test suite failed! Aborting packaging.
    exit /b 1
)
echo [SUCCESS] All tests passed.

echo [2/4] Generating application icon assets...
python scripts\generate_icons.py
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Icon generation failed, proceeding with existing assets.
)

echo [3/4] Packaging Windows executable with PyInstaller...
pyinstaller --clean --noconfirm TradeAudit.spec
if %ERRORLEVEL% neq 0 (
    echo [ERROR] PyInstaller packaging failed!
    exit /b 1
)

echo [4/4] Verifying build output...
if exist "dist\TradeAudit\TradeAudit.exe" (
    echo =======================================================
    echo  BUILD SUCCESSFUL: dist\TradeAudit\TradeAudit.exe
    echo =======================================================
) else (
    echo [ERROR] Executable dist\TradeAudit\TradeAudit.exe was not created!
    exit /b 1
)

endlocal
