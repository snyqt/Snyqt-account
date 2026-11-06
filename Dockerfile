# ============================================
# SNYQT Account - Docker 镜像 (uWSGI)
# 本文件只包含公开、非敏感默认参数；
# 密钥/密码/Token 全部由运行时环境变量（Gitea Actions Secrets）注入。
# ============================================

# 使用 Python 3.11 slim 版本（通过 DaoCloud 镜像加速）
FROM docker.m.daocloud.io/python:3.11-slim

WORKDIR /app

# 切换为国内镜像源（避免官方源 502/403）
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null \
    || sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    libssl-dev \
    libjpeg-dev \
    zlib1g-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

COPY requirements.txt .

RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ --upgrade pip && \
    pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt

COPY . .

# 创建运行所需目录（须在 VOLUME 声明之前，确保镜像内初始内容可继承）
RUN mkdir -p /app/logs /app/static/img/user_avatar /app/static/temp

# ============================================
# 数据持久化卷
# ============================================
VOLUME ["/app/static/img/user_avatar"]
VOLUME ["/app/static/temp"]
VOLUME ["/app/logs"]

# ============================================
# 环境变量配置（仅公开默认值）
# 注意：SECRET_KEY / DB_PASSWORD / SMTP_PASSWORD /
# ALIYUN_ACCESS_KEY_* / TURNSTILE_SECRET_KEY 等敏感项
# 严禁写入镜像，必须在 docker run -e 时注入。
# ============================================
ENV FLASK_ENV=production
ENV UWSGI_MODE=true
ENV TIMEZONE=Asia/Shanghai
ENV LANG=C.UTF-8
ENV APP_PORT=5000
ENV TURNSTILE_VERIFY_URL=https://challenges.cloudflare.com/turnstile/v0/siteverify

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/')" || exit 1

CMD ["uwsgi", "--http", "0.0.0.0:5000", "--wsgi-file", "run.py", "--callable", "app", "--processes", "2", "--threads", "4", "--enable-threads"]
