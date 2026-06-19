#!/bin/bash
# ============================================
# SNYQT 统一账户认证系统 - Docker 打包脚本
# ============================================
# 所有配置已硬编码在 config.py 中，无需环境变量
# 用法: bash build.sh
# 输出: dist/snyqt-account_v1.0.0.tar.gz
# ============================================

set -e

VERSION="${1:-1.0.0}"
IMAGE_NAME="snyqt-account"
OUTPUT_DIR="dist"

echo "========================================"
echo "  SNYQT 账户认证系统 - Docker 打包"
echo "========================================"
echo ""

echo "[1/5] 检查 Docker 环境..."
docker --version
echo ""

echo "[2/5] 清理旧镜像..."
docker rmi "${IMAGE_NAME}:latest" 2>/dev/null || true
docker rmi "${IMAGE_NAME}:v${VERSION}" 2>/dev/null || true

echo "[3/5] 构建 Docker 镜像 (${IMAGE_NAME}:v${VERSION})..."
docker build -t "${IMAGE_NAME}:v${VERSION}" -t "${IMAGE_NAME}:latest" .
echo "  镜像构建成功!"

mkdir -p "${OUTPUT_DIR}"

TAR_FILE="${OUTPUT_DIR}/${IMAGE_NAME}_v${VERSION}.tar"
GZ_FILE="${TAR_FILE}.gz"

echo "[4/5] 导出 Docker 镜像..."
docker save -o "${TAR_FILE}" "${IMAGE_NAME}:v${VERSION}"
gzip -f "${TAR_FILE}"
echo "  导出完成: ${GZ_FILE}"

echo "[5/5] 打包完成!"
echo ""
echo "========================================"
echo "  输出文件:"
echo "========================================"
ls -lh "${GZ_FILE}"
echo ""
echo "========================================"
echo "  一键部署命令 (目标机器):"
echo "========================================"
echo "  # 1. 加载镜像"
echo "  gunzip -c ${GZ_FILE} | docker load"
echo ""
echo "  # 2. 一键启动（无需任何环境变量）"
echo "  docker run -d --name snyqt-account -p 80:5000 ${IMAGE_NAME}:v${VERSION}"
echo ""
echo "  # 或使用 docker-compose"
echo "  docker-compose up -d"