# -*- coding: utf-8 -*-
"""
配置文件示例 - 复制此文件为 config.py 并填入你的配置信息
"""

import os

# ==================== 环境模式配置 ====================
# 可选值: 'auto' (自动检测), 'production' (强制生产环境), 'development' (强制测试环境)
# 在 Docker + uWSGI 真实生产环境下，此配置项不生效，始终使用生产环境模式
ENVIRONMENT_MODE = os.getenv('ENVIRONMENT_MODE', 'auto')

# ==================== 应用端口配置 ====================
# 统一所有环境的端口号
APP_PORT = int(os.getenv('APP_PORT', 5000))

# ==================== 时区配置 ====================
TIMEZONE = 'Asia/Shanghai'

# ==================== 数据库配置 ====================
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'your_db_user'),
    'password': os.getenv('DB_PASSWORD', 'your_db_password'),
    'database': os.getenv('DB_NAME', 'Snyqt-account'),
}

# ==================== Flask密钥配置 ====================
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-this-in-production')

# ==================== 邮箱 SMTP 配置 ====================
EMAIL_CONFIG = {
    'smtp_server': os.getenv('SMTP_SERVER', 'smtp.exmail.qq.com'),
    'port': int(os.getenv('SMTP_PORT', 465)),
    'sender': os.getenv('SMTP_SENDER', 'your-email@example.com'),
    'password': os.getenv('SMTP_PASSWORD', 'your-email-password')
}

# ==================== 阿里云短信服务配置 ====================
ALIYUN_SMS_CONFIG = {
    'access_key_id': os.getenv('ALIYUN_ACCESS_KEY_ID', 'your-access-key-id'),
    'access_key_secret': os.getenv('ALIYUN_ACCESS_KEY_SECRET', 'your-access-key-secret'),
    'sign_name': os.getenv('ALIYUN_SIGN_NAME', '您的短信签名'),
    'template_code': os.getenv('ALIYUN_TEMPLATE_CODE', 'SMS_XXXXXXX'),
}

# ==================== Cloudflare Turnstile 配置 ====================
# TURNSTILE_ENABLED: 是否启用全局人机验证
# - 设置为 'true' 强制启用
# - 设置为 'false' 强制禁用
# - 不设置或留空则在生产环境自动启用，开发环境禁用
TURNSTILE_ENABLED = os.getenv('TURNSTILE_ENABLED', '')

TURNSTILE_CONFIG = {
    'secret_key': os.getenv('TURNSTILE_SECRET_KEY', 'your-turnstile-secret-key'),
    'site_key': os.getenv('TURNSTILE_SITEKEY', 'your-turnstile-site-key'),
    'verify_url': os.getenv('TURNSTILE_VERIFY_URL', 'https://challenges.cloudflare.com/turnstile/v0/siteverify'),
}

# ==================== 短信验证码有效期 ====================
VERIFICATION_CODE_EXPIRE = int(os.getenv('VERIFICATION_CODE_EXPIRE', 300))

# ==================== 登录安全配置 ====================
ENABLE_2FA = False

RISK_CONTROL = {
    'enabled': True,
    '异地登录检测': True,
    '新设备检测': True,
    '失败次数阈值': 3,
}

# ==================== IP定位配置 ====================
IP_LOCATION_API = 'http://ip-api.com/json/'

# ==================== 项目信息配置 ====================
PROJECT_NAME = '少年友晴天-统一账户认证系统'
PROJECT_VERSION = '1.0.0'
PROJECT_EMAIL = 'snyqt@qq.com'
PROJECT_QQ_GROUP = '1106802055'
PROJECT_WEBSITE = 'account.snyqt.top'

# ==================== 记住我功能 ====================
REMEMBER_ME_COOKIE_DURATION = 7
SESSION_DURATION = 10
