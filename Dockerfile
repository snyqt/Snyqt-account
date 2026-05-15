FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 数据库配置
ENV DB_HOST=localhost \
    DB_USER=snyqt-study \
    DB_PASSWORD=your_password_here \
    DB_NAME=Snyqt-study-sql

# Flask密钥配置
ENV SECRET_KEY=change-this-to-a-random-secret-key-in-production

# 邮箱SMTP配置
ENV SMTP_SERVER=smtp.qq.com \
    SMTP_PORT=587 \
    EMAIL_SENDER=your-email@qq.com \
    EMAIL_PASSWORD=your-email-auth-code

# 阿里云短信服务配置
ENV ALIYUN_ACCESS_KEY_ID=your-aliyun-access-key-id \
    ALIYUN_ACCESS_KEY_SECRET=your-aliyun-access-key-secret \
    ALIYUN_SIGN_NAME=your-sms-sign-name \
    ALIYUN_TEMPLATE_CODE=your-sms-template-code

# Cloudflare Turnstile配置
ENV TURNSTILE_SECRET_KEY=your-turnstile-secret-key \
    TURNSTILE_SITEKEY=your-turnstile-site-key \
    TURNSTILE_VERIFY_URL=https://challenges.cloudflare.com/turnstile/v0/siteverify 

# 其他配置

ENV VERIFICATION_CODE_EXPIRE=300 \
    ENABLE_2FA=False \
    RISK_CONTROL_ENABLED=True \
    RISK_CONTROL_REMOTE_LOGIN=True \
    RISK_CONTROL_NEW_DEVICE=True \
    RISK_CONTROL_FAILED_LOGIN=3 \
    IP_LOCATION_API=http://ip-api.com/json/ \
    REMEMBER_ME_COOKIE_DURATION=7 \
    SESSION_DURATION=10 

# uWSGI模式标志（用于启用Turnstile）
ENV UWSGI_MODE=true

EXPOSE 80

CMD ["uwsgi", "uwsgi.ini"]
