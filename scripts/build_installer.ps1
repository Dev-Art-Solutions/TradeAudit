# PowerShell Build Pipeline for TradeAudit Windows Installer and Release Packages
$ErrorActionPreference = "Stop"

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "       TradeAudit Release & Installer Build Pipeline" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan

# 1. Automated Test Suite
Write-Host "`n[1/5] Running automated test suite..." -ForegroundColor Yellow
pytest tests\unit
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Test suite failed! Packaging aborted." -ForegroundColor Red
    exit 1
}
Write-Host "[SUCCESS] All unit tests passed." -ForegroundColor Green

# 2. Asset Generation
Write-Host "`n[2/5] Generating application icon assets..." -ForegroundColor Yellow
python scripts\generate_icons.py

# 3. PyInstaller Build
Write-Host "`n[3/5] Packaging Windows executable with PyInstaller..." -ForegroundColor Yellow
pyinstaller --clean --noconfirm TradeAudit.spec
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] PyInstaller packaging failed!" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path "dist\TradeAudit\TradeAudit.exe")) {
    Write-Host "[ERROR] Target executable dist\TradeAudit\TradeAudit.exe not found!" -ForegroundColor Red
    exit 1
}
Write-Host "[SUCCESS] PyInstaller build verified at dist\TradeAudit\TradeAudit.exe" -ForegroundColor Green

# Read version from src/tradeaudit/__init__.py - the single source of truth
# also used at runtime (Settings.app_version) and in pyproject.toml.
$version = "1.0.0"
if (Test-Path "src\tradeaudit\__init__.py") {
    $content = Get-Content "src\tradeaudit\__init__.py" -Raw
    if ($content -match '__version__\s*=\s*"([^"]+)"') {
        $version = $matches[1]
    }
}

# 4. Create Portable ZIP Release
Write-Host "`n[4/5] Creating portable ZIP release package..." -ForegroundColor Yellow
$zipOutput = "dist\TradeAudit-v$version-win64-portable.zip"
if (Test-Path $zipOutput) {
    Remove-Item $zipOutput -Force
}
Compress-Archive -Path "dist\TradeAudit\*" -DestinationPath $zipOutput -CompressionLevel Optimal
Write-Host "[SUCCESS] Portable archive created: $zipOutput" -ForegroundColor Green

# 5. Build Windows Setup Installer with Inno Setup
Write-Host "`n[5/5] Compiling Inno Setup Installer..." -ForegroundColor Yellow

$isccCandidates = @(
    "ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 5\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 5\ISCC.exe",
    "${env:LOCALAPPDATA}\Programs\Inno Setup 6\ISCC.exe"
)

$isccPath = $null
foreach ($candidate in $isccCandidates) {
    if ($candidate -eq "ISCC.exe") {
        $cmd = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
        if ($cmd) {
            $isccPath = $cmd.Source
            break
        }
    } elseif (Test-Path $candidate) {
        $isccPath = $candidate
        break
    }
}

if ($isccPath) {
    Write-Host "Found Inno Setup Compiler at: $isccPath" -ForegroundColor Cyan
    & $isccPath "/DMyAppVersion=$version" "installer\TradeAudit.iss"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Inno Setup compilation failed!" -ForegroundColor Red
        exit 1
    }

    $setupExe = "dist\installer\TradeAudit-Setup-v$version.exe"
    if (Test-Path $setupExe) {
        Write-Host "`n=======================================================" -ForegroundColor Green
        Write-Host " INSTALLER BUILD SUCCESSFUL!" -ForegroundColor Green
        Write-Host " Setup Executable: $setupExe" -ForegroundColor Green
        Write-Host " Portable ZIP:     $zipOutput" -ForegroundColor Green
        Write-Host "=======================================================" -ForegroundColor Green
    } else {
        Write-Host "[WARNING] Inno Setup finished but $setupExe was not found." -ForegroundColor Yellow
    }
} else {
    Write-Host "[NOTE] Inno Setup Compiler (ISCC.exe) not detected on PATH or standard directories." -ForegroundColor Yellow
    Write-Host "To compile the Windows installer executable (TradeAudit-Setup.exe):" -ForegroundColor Cyan
    Write-Host "  1. Install Inno Setup 6 (e.g. 'winget install JRSoftware.InnoSetup' or from https://jrsoftware.org/isdl.php)" -ForegroundColor Cyan
    Write-Host "  2. Run: scripts\build_installer.ps1 or compile installer\TradeAudit.iss directly in Inno Setup IDE." -ForegroundColor Cyan
    Write-Host "`n[SUCCESS] Portable release package is ready at: $zipOutput" -ForegroundColor Green
}
