# ============================================
# SNYQT 统一账户认证系统 - Docker 镜像
# ============================================
# 基于 Python 3.11-slim 镜像构建
# 所有配置已硬编码在 config.py 中，无需环境变量
#
# 构建命令：
#   docker build -t snyqt-account .
#
# 运行命令（一键部署）：
#   docker run -d --name snyqt-account -p 80:5000 snyqt-account
# ============================================

FROM python:3.11-slim

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    libjpeg-dev \
    libz-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 应用代码（包含 config.py 硬编码配置）
COPY . .

# 时区
ENV TZ=Asia/Shanghai

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000')" || exit 1

CMD ["uwsgi", "uwsgi.ini"]