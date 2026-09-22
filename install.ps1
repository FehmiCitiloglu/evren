# EVREN CLI & Agent — Windows PowerShell Installer
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "EVREN CLI & Agent Windows Kurulumu başlatılıyor..." -ForegroundColor Cyan

if (Get-Command py -ErrorAction SilentlyContinue) {
    py -3 install.py @args
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    python install.py @args
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    python3 install.py @args
} else {
    Write-Error "Python 3 bulunamadı. Lütfen Python 3.10+ kurun: winget install Python.Python.3.12 veya winget install astral-sh.uv"
    exit 1
}
