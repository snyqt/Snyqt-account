# -*- coding: utf-8 -*-
"""
配置文件示例 - 请复制此文件为 config.py 并填入你的配置信息

使用方法：
1. 复制 config.example.py 为 config.py
2. 修改 config.py 中的配置项
3. 不要将 config.py 提交到代码仓库（已在.gitignore中忽略）
"""

import os

# ==================== 时区配置 ====================
TIMEZONE = 'Asia/Shanghai'

# ==================== 数据库配置 ====================
# 推荐使用环境变量，在生产环境中更安全
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'your_db_user'),
    'password': os.getenv('DB_PASSWORD', 'your_db_password'),
    'database': os.getenv('DB_NAME', 'Snyqt-study-sql'),
}

# ==================== Flask密钥配置 ====================
# 务必在生产环境中使用强密钥！
# 生成随机密钥的方法：在Python中执行 import secrets; secrets.token_hex(32)
SECRET_KEY = os.getenv('SECRET_KEY', 'change-this-to-a-random-secret-key')

# ==================== 邮箱 SMTP 配置 ====================
# 以QQ邮箱为例，其他邮箱服务请修改对应配置
EMAIL_CONFIG = {
    'smtp_server': os.getenv('SMTP_SERVER', 'smtp.qq.com'),  # SMTP服务器地址
    'port': int(os.getenv('SMTP_PORT', 587)),  # SMTP端口（QQ邮箱使用587，SSL使用465）
    'sender': os.getenv('EMAIL_SENDER', 'your-email@qq.com'),  # 发件人邮箱
    'password': os.getenv('EMAIL_PASSWORD', 'your-email-auth-code'),  # 邮箱授权码（非登录密码）
    # 获取授权码：QQ邮箱 -> 设置 -> 账户 -> POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务
}

# ==================== 阿里云短信服务配置 ====================
# 申请地址：https://dysms.console.aliyun.com/
ALIYUN_SMS_CONFIG = {
    'access_key_id': os.getenv('ALIYUN_ACCESS_KEY_ID', 'your-aliyun-access-key-id'),  # 阿里云AccessKey ID
    'access_key_secret': os.getenv('ALIYUN_ACCESS_KEY_SECRET', 'your-aliyun-access-key-secret'),  # 阿里云AccessKey Secret
    'sign_name': os.getenv('ALIYUN_SIGN_NAME', 'your-sms-sign-name'),  # 短信签名（在阿里云控制台申请）
    'template_code': os.getenv('ALIYUN_TEMPLATE_CODE', 'your-sms-template-code'),  # 短信模板CODE（在阿里云控制台申请）
}

# ==================== Cloudflare Turnstile 配置 ====================
# 免费的人机验证服务，替代Google reCAPTCHA
# 申请地址：https://dash.cloudflare.com/ -> Turnstile
# 开发环境使用测试密钥，生产环境使用真实密钥
TURNSTILE_CONFIG = {
    'secret_key': os.getenv('TURNSTILE_SECRET_KEY', 'your-turnstile-secret-key'),
    'site_key': os.getenv('TURNSTILE_SITEKEY', 'your-turnstile-site-key'),
    'verify_url': os.getenv('TURNSTILE_VERIFY_URL', 'https://challenges.cloudflare.com/turnstile/v0/siteverify'),
    'enabled': os.getenv('TURNSTILE_ENABLED', False),  # 开发环境设为False（使用测试密钥），生产环境设为True
}

# ==================== 短信验证码有效期 ====================
VERIFICATION_CODE_EXPIRE = int(os.getenv('VERIFICATION_CODE_EXPIRE', 300))  # 5分钟，单位：秒

# ==================== 登录安全配置 ====================
# 是否强制启用两步验证（所有用户登录都需要验证码）
ENABLE_2FA = os.getenv('ENABLE_2FA', False)

# 风控检测配置
RISK_CONTROL = {
    'enabled': os.getenv('RISK_CONTROL_ENABLED', True),  # 是否启用风控检测
    '异地登录检测': os.getenv('RISK_CONTROL_REMOTE_LOGIN', True),  # 检测是否与上次登录地点不同
    '新设备检测': os.getenv('RISK_CONTROL_NEW_DEVICE', True),  # 检测是否使用新设备登录
    '失败次数阈值': int(os.getenv('RISK_CONTROL_FAILED_LOGIN', 3)),  # 登录失败多少次后触发风控
}

# ==================== IP定位配置 ====================
# 使用免费的IP定位API
IP_LOCATION_API = os.getenv('IP_LOCATION_API', 'http://ip-api.com/json/')

# ==================== 记住我功能 ====================
REMEMBER_ME_COOKIE_DURATION = int(os.getenv('REMEMBER_ME_COOKIE_DURATION', 7))  # 天数
SESSION_DURATION = int(os.getenv('SESSION_DURATION', 10))  # 分钟（未勾选记住我时）
