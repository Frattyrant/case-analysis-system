# 在项目根目录生成 dist\case_analysis.exe（单文件、无控制台）
# 用法: .\scripts\build_exe.ps1

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (Test-Path "requirements.txt") {
    python -m pip install -r requirements.txt -q
}
python -m pip install -r requirements-build.txt -q
python -m PyInstaller case_analysis.spec --noconfirm

Write-Host "输出: dist\case_analysis.exe"
