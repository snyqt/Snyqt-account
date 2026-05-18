from app.env import env

def auto_configure():
    is_production = env.is_production()
    environment = env.get_environment()
    
    result = {
        'environment': environment,
        'is_production': is_production,
        'debug': not is_production,
        'port': 80 if is_production else 5495,
    }
    
    return result

def configure_turnstile():
    from config import TURNSTILE_CONFIG
    
    is_production = env.is_production()
    
    turnstile_enabled = True if is_production else False
    
    if os.getenv('TURNSTILE_ENABLED', '').lower() == 'true':
        turnstile_enabled = True
    
    return {
        **TURNSTILE_CONFIG,
        'enabled': turnstile_enabled
    }

def configure_risk_control():
    from config import RISK_CONTROL
    
    is_production = env.is_production()
    
    risk_control = RISK_CONTROL.copy()
    risk_control['失败次数阈值'] = 3 if is_production else 5
    
    return risk_control

import os
