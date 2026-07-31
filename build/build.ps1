# Build the "解压即用" folder + zip for Windows.
# Usage: powershell -ExecutionPolicy Bypass -File build/build.ps1
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$python = "python"

Write-Host "==> Installing build dependencies"
& $python -m pip install --upgrade pip
& $python -m pip install -r requirements.txt pyinstaller
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> Downloading static ffmpeg"
& $python build/download_ffmpeg.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> Running PyInstaller"
if (Test-Path "build/work") { Remove-Item -Recurse -Force "build/work" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
& $python -m PyInstaller batch_lut.spec --workpath build/work --distpath dist
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> Creating zip"
Compress-Archive -Path "dist/DJI LUT" -DestinationPath "dist/DJI-LUT-Converter-Windows.zip" -Force
Write-Host "==> dist/DJI-LUT-Converter-Windows.zip"
