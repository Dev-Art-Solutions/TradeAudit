# PowerShell Build Pipeline for TradeAudit Windows Executable
$ErrorActionPreference = "Stop"

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "          TradeAudit Production Build Pipeline" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan

Write-Host "`n[1/4] Running automated test suite..." -ForegroundColor Yellow
pytest tests\unit
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Test suite failed! Packaging aborted." -ForegroundColor Red
    exit 1
}
Write-Host "[SUCCESS] All unit tests passed." -ForegroundColor Green

Write-Host "`n[2/4] Generating application icon assets..." -ForegroundColor Yellow
python scripts\generate_icons.py

Write-Host "`n[3/4] Packaging Windows executable with PyInstaller..." -ForegroundColor Yellow
pyinstaller --clean --noconfirm TradeAudit.spec
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] PyInstaller packaging failed!" -ForegroundColor Red
    exit 1
}

Write-Host "`n[4/4] Verifying build output..." -ForegroundColor Yellow
if (Test-Path "dist\TradeAudit\TradeAudit.exe") {
    Write-Host "=======================================================" -ForegroundColor Green
    Write-Host " BUILD SUCCESSFUL: dist\TradeAudit\TradeAudit.exe" -ForegroundColor Green
    Write-Host "=======================================================" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Target executable dist\TradeAudit\TradeAudit.exe not found!" -ForegroundColor Red
    exit 1
}
