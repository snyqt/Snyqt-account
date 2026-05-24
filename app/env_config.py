from app.env import env
import os

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
    from config import TURNSTILE_CONFIG
    
    turnstile_enabled = False
    
    env_var = os.getenv('TURNSTILE_ENABLED', '').lower()
    if env_var == 'true':
        turnstile_enabled = True
    elif env_var == 'false':
        turnstile_enabled = False
    else:
        is_production = env.should_use_production()
        turnstile_enabled = True if is_production else False
    
    print(f"[配置信息] Cloudflare Turnstile: {'启用' if turnstile_enabled else '禁用'}")
    
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
