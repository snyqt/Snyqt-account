from app.env import env
import os
import urllib.request
import socket

def auto_configure():
    is_production = env.should_use_production()
    environment = env.get_environment()
    
    port = int(os.getenv('APP_PORT', 5000))
    
    print(f"[配置信息] 运行环境: {env.get_run_mode()}")
    print(f"[配置信息] 环境类型: {environment}")
    print(f"[配置信息] 端口: {port}")
    
    result = {
        'environment': environment,
        'is_production': is_production,
        'debug': not is_production,
        'port': port,
    }
    
    return result

def configure_turnstile():
    from config import TURNSTILE_CONFIG, TURNSTILE_ENABLED

    turnstile_enabled = False

    # 优先使用环境变量配置
    env_var = os.getenv('TURNSTILE_ENABLED', TURNSTILE_ENABLED or '').lower()
    if env_var == 'true':
        turnstile_enabled = True
    elif env_var == 'false':
        turnstile_enabled = False
    else:
        # 未设置时，根据环境自动决定
        is_production = env.should_use_production()
        turnstile_enabled = True if is_production else False

    print(f"[配置信息] Cloudflare Turnstile 全局验证: {'启用' if turnstile_enabled else '禁用'}")

    return {
        **TURNSTILE_CONFIG,
        'enabled': turnstile_enabled
    }

def configure_risk_control():
    from config import RISK_CONTROL
    
    is_production = env.should_use_production()
    
    risk_control = RISK_CONTROL.copy()
    risk_control['失败次数阈值'] = 3 if is_production else 5
    
    return risk_control

def configure_force_mfa():
    from config import FORCE_MFA
    print(f"[配置信息] 强制多因子认证 (FORCE_MFA): {'启用' if FORCE_MFA else '禁用（仅风控异常时触发）'}")
    return FORCE_MFA

def log_public_ipv6():
    """输出公网 IPv6 地址"""
    try:
        # 方法1：通过外部服务获取 IPv6 地址
        req = urllib.request.Request('https://ipv6.icanhazip.com', headers={'User-Agent': 'curl/7.0'})
        resp = urllib.request.urlopen(req, timeout=5)
        ipv6 = resp.read().decode().strip()
        print(f"[公网IPv6] {ipv6}")
    except Exception:
        # 方法2：尝试备用服务
        try:
            req = urllib.request.Request('https://api6.ipify.org', headers={'User-Agent': 'curl/7.0'})
            resp = urllib.request.urlopen(req, timeout=5)
            ipv6 = resp.read().decode().strip()
            print(f"[公网IPv6] {ipv6}")
        except Exception:
            print("[公网IPv6] 无法获取（可能未启用IPv6或网络受限）")
