# ============================================
# SNYQT 统一账户认证系统 - Docker 打包脚本 (Windows)
# ============================================
# 所有配置已硬编码在 config.py 中，无需环境变量
# 用法: .\build.ps1
# 输出: dist/snyqt-account_v1.0.0.tar.gz
# ============================================

param(
    [string]$Version = "1.0.0",
    [string]$ImageName = "snyqt-account",
    [string]$OutputDir = "dist"
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SNYQT 账户认证系统 - Docker 打包" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/5] 检查 Docker 环境..." -ForegroundColor Yellow
$dockerVersion = docker --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误: Docker 未安装或未运行!" -ForegroundColor Red
    exit 1
}
Write-Host "  $dockerVersion" -ForegroundColor Green

Write-Host "[2/5] 清理旧镜像..." -ForegroundColor Yellow
docker rmi "${ImageName}:latest" 2>$null
docker rmi "${ImageName}:v${Version}" 2>$null

Write-Host "[3/5] 构建 Docker 镜像 (${ImageName}:v${Version})..." -ForegroundColor Yellow
docker build -t "${ImageName}:v${Version}" -t "${ImageName}:latest" .
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误: Docker 构建失败!" -ForegroundColor Red
    exit 1
}
Write-Host "  镜像构建成功!" -ForegroundColor Green

if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

$tarFile = "${OutputDir}/${ImageName}_v${Version}.tar"
$gzFile = "${tarFile}.gz"

Write-Host "[4/5] 导出 Docker 镜像到 $tarFile ..." -ForegroundColor Yellow
docker save -o $tarFile "${ImageName}:v${Version}"
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误: docker save 失败!" -ForegroundColor Red
    exit 1
}

Write-Host "  压缩为 $gzFile ..." -ForegroundColor Yellow
Compress-Archive -Path $tarFile -DestinationPath $gzFile -Force
Remove-Item $tarFile -Force

Write-Host "[5/5] 打包完成!" -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  输出文件:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
$fileInfo = Get-Item $gzFile
$sizeMB = [math]::Round($fileInfo.Length / 1MB, 2)
Write-Host "  文件: $gzFile" -ForegroundColor Green
Write-Host "  大小: ${sizeMB} MB" -ForegroundColor Green
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  一键部署命令 (目标机器):" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  # 1. 加载镜像" -ForegroundColor White
Write-Host "  docker load -i ${ImageName}_v${Version}.tar.gz" -ForegroundColor White
Write-Host ""
Write-Host "  # 2. 一键启动（无需任何环境变量）" -ForegroundColor White
Write-Host "  docker run -d --name snyqt-account -p 80:5000 ${ImageName}:v${Version}" -ForegroundColor White
Write-Host ""
Write-Host "  # 或使用 docker-compose" -ForegroundColor White
Write-Host "  docker-compose up -d" -ForegroundColor White