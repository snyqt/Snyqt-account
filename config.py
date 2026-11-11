# -*- coding: utf-8 -*-
"""
应用配置：只从环境变量读取，不包含任何明文密钥，可安全提交到公开仓库。

- 必填项（密钥、密码、账号等）读取为空时，导入本模块即抛异常并拒绝启动。
- 非敏感可选项提供安全默认值；环境变量为空字符串时同样回退默认值，
  避免 docker -e KEY= 的空值覆盖。
"""

import os


def _get_required(name):
    """读取必填环境变量，未配置（含空字符串）返回 None"""
    value = os.getenv(name)
    if value is None or value.strip() == '':
        return None
    return value.strip()


def _get_optional(name, default):
    """读取可选环境变量，未配置或为空时返回默认值"""
    value = os.getenv(name)
    if value is None or value.strip() == '':
        return default
    return value.strip()


def _get_optional_int(name, default):
    value = _get_optional(name, None)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        raise RuntimeError(f'环境变量 {name} 必须是整数，当前值无法解析：{value!r}')


def _get_optional_bool(name, default):
    value = _get_optional(name, None)
    if value is None:
        return default
    return value.lower() in ('1', 'true', 'yes', 'on')


# ==================== 必填项清单 ====================
# 说明：敏感项必须由部署者在 Gitea Actions Secrets（或本地环境变量）中配置。
REQUIRED_ENV_VARS = {
    'SECRET_KEY': 'Flask 会话签名密钥（随机字符串，建议 32 位以上）',
    'DB_USER': '数据库用户名',
    'DB_PASSWORD': '数据库密码',
    'SMTP_SENDER': '发件人邮箱地址',
    'SMTP_PASSWORD': 'SMTP 授权码 / 登录密码',
    'ALIYUN_ACCESS_KEY_ID': '阿里云短信 AccessKey ID',
    'ALIYUN_ACCESS_KEY_SECRET': '阿里云短信 AccessKey Secret',
    'TURNSTILE_SECRET_KEY': 'Cloudflare Turnstile 服务端密钥',
}


def validate_config():
    """一次性校验全部必填环境变量，缺失则立即失败（fail fast）"""
    missing = [name for name in REQUIRED_ENV_VARS if _get_required(name) is None]

    if missing:
        detail = '\n'.join(f'  - {name}：{REQUIRED_ENV_VARS[name]}' for name in missing)
        raise RuntimeError(
            '缺少必需的环境变量，应用拒绝启动：\n'
            f'{detail}\n'
            '本地开发请在 .env 或 shell 环境变量中配置；'
            '生产环境请在 Gitea 仓库 Settings → Actions → Secrets 中配置后重新部署。'
        )


validate_config()

# ==================== 环境模式配置 ====================
ENVIRONMENT_MODE = _get_optional('ENVIRONMENT_MODE', 'auto')

# ==================== 应用端口配置 ====================
APP_PORT = _get_optional_int('APP_PORT', 5000)

# ==================== 时区配置 ====================
TIMEZONE = _get_optional('TIMEZONE', 'Asia/Shanghai')

# ==================== 数据库配置 ====================
DB_CONFIG = {
    'host': _get_optional('DB_HOST', 'localhost'),
    'port': _get_optional_int('DB_PORT', 3306),
    'user': _get_required('DB_USER'),
    'password': _get_required('DB_PASSWORD'),
    'database': _get_optional('DB_NAME', 'Snyqt-account'),
}

# ==================== Flask密钥配置 ====================
SECRET_KEY = _get_required('SECRET_KEY')

# ==================== 邮箱 SMTP 配置 ====================
EMAIL_CONFIG = {
    'smtp_server': _get_optional('SMTP_SERVER', 'smtp.exmail.qq.com'),
    'port': _get_optional_int('SMTP_PORT', 465),
    'sender': _get_required('SMTP_SENDER'),
    'password': _get_required('SMTP_PASSWORD'),
}

# ==================== 阿里云短信服务配置 ====================
ALIYUN_SMS_CONFIG = {
    'access_key_id': _get_required('ALIYUN_ACCESS_KEY_ID'),
    'access_key_secret': _get_required('ALIYUN_ACCESS_KEY_SECRET'),
    'sign_name': _get_optional('ALIYUN_SIGN_NAME', '速通互联验证码'),
    'template_code': _get_optional('ALIYUN_TEMPLATE_CODE', '100001'),
}

# ==================== Cloudflare Turnstile 配置 ====================
TURNSTILE_ENABLED = _get_optional('TURNSTILE_ENABLED', 'false')

TURNSTILE_CONFIG = {
    'secret_key': _get_required('TURNSTILE_SECRET_KEY'),
    'site_key': _get_optional('TURNSTILE_SITEKEY', '0x4AAAAAACyxdKEqrmJV4bJn'),
    'verify_url': _get_optional(
        'TURNSTILE_VERIFY_URL',
        'https://challenges.cloudflare.com/turnstile/v0/siteverify'
    ),
}

# ==================== 短信验证码有效期 ====================
VERIFICATION_CODE_EXPIRE = _get_optional_int('VERIFICATION_CODE_EXPIRE', 300)

# ==================== 登录安全配置 ====================
ENABLE_2FA = False

# 是否强制启用多因子认证（MFA）
FORCE_MFA = _get_optional_bool('FORCE_MFA', True)

# WebAuthn/FIDO2 安全密钥配置（生产环境域名）
WEBAUTHN_RP_ID = _get_optional('WEBAUTHN_RP_ID', 'account.snyqt.top')
WEBAUTHN_ORIGIN = _get_optional('WEBAUTHN_ORIGIN', 'https://account.snyqt.top')

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
PROJECT_EMAIL = _get_optional('PROJECT_EMAIL', 'snyqt@qq.com')
PROJECT_QQ_GROUP = '1106802055'
PROJECT_WEBSITE = 'account.snyqt.top'

# ==================== 记住我功能 ====================
REMEMBER_ME_COOKIE_DURATION = 7
SESSION_DURATION = 10
