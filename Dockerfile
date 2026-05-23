# ============================================
# SNYQT 统一账户认证系统 - Docker 镜像
# ============================================
# 基于 Python 3.11-slim 镜像构建
# 
# 构建命令：
#   docker build -t snyqt-account .
#
# 运行命令：
#   docker run -d --name snyqt-account -p 80:80 \
#     -e DB_HOST=your_db_host \
#     -e DB_USER=your_db_user \
#     -e DB_PASSWORD=your_db_password \
#     -e DB_NAME=Snyqt-account \
#     -e SECRET_KEY=your-secret-key \
#     -e SMTP_SENDER=your-email@qq.com \
#     -e SMTP_PASSWORD=your-email-auth-code \
#     snyqt-account

# 使用 Python 3.11 slim 版本
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# ============================================
# 第一阶段：安装系统依赖
# ============================================
RUN apt-get update && apt-get install -y --no-install-recommends \
    # 编译工具
    gcc \
    libc6-dev \
    # 图片处理依赖
    libjpeg-dev \
    libz-dev \
    # SSL证书
    ca-certificates \
    # 清理缓存
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# ============================================
# 第二阶段：安装 Python 依赖
# ============================================
# 先复制 requirements.txt 以利用 Docker 缓存
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# ============================================
# 第三阶段：复制应用代码
# ============================================
# 复制应用代码到容器
COPY . .

# ============================================
# 环境变量配置
# ============================================

# 数据库配置
ENV DB_HOST=localhost
ENV DB_USER=snyqt_user
ENV DB_PASSWORD=change_password_in_production
ENV DB_NAME=Snyqt-account

# Flask密钥配置（务必在生产环境修改）
ENV SECRET_KEY=change-this-to-a-random-secret-key-in-production

# 邮箱SMTP配置
ENV SMTP_SERVER=smtp.qq.com
ENV SMTP_PORT=587
ENV SMTP_SENDER=your-email@qq.com
ENV SMTP_PASSWORD=your-email-auth-code

# 阿里云短信服务配置（可选）
ENV ALIYUN_ACCESS_KEY_ID=your-aliyun-access-key-id
ENV ALIYUN_ACCESS_KEY_SECRET=your-aliyun-access-key-secret
ENV ALIYUN_SIGN_NAME=your-sms-sign-name
ENV ALIYUN_TEMPLATE_CODE=your-sms-template-code

# Cloudflare Turnstile配置（可选）
ENV TURNSTILE_SECRET_KEY=your-turnstile-secret-key
ENV TURNSTILE_SITEKEY=your-turnstile-site-key
ENV TURNSTILE_VERIFY_URL=https://challenges.cloudflare.com/turnstile/v0/siteverify

# 安全配置
ENV ENABLE_2FA=False
ENV RISK_CONTROL_ENABLED=True

# 验证码配置
ENV VERIFICATION_CODE_EXPIRE=300

# 会话配置
ENV REMEMBER_ME_COOKIE_DURATION=7
ENV SESSION_DURATION=10

# IP定位API
ENV IP_LOCATION_API=http://ip-api.com/json/

# uWSGI模式标志
ENV UWSGI_MODE=true

# 时区配置
ENV TIMEZONE=Asia/Shanghai

# 项目信息
ENV PROJECT_NAME=少年友晴天-统一账户认证系统
ENV PROJECT_VERSION=1.0.0
ENV PROJECT_EMAIL=snyqt@qq.com
ENV PROJECT_QQ_GROUP=1106802055
ENV PROJECT_WEBSITE=account.snyqt.top

# ============================================
# 暴露端口
# ============================================
EXPOSE 80

# ============================================
# 健康检查
# ============================================
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:80')" || exit 1

# ============================================
# 启动命令
# ============================================
# 使用 uWSGI 运行应用
CMD ["uwsgi", "uwsgi.ini"]
