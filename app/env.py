import os
import socket

class Environment:
    def __init__(self):
        self.local_hosts = ['localhost', '127.0.0.1', '::1']
        self.private_ip_prefixes = [
            '192.168.', '10.', '172.16.', '172.17.', '172.18.', '172.19.', '172.20.',
            '172.21.', '172.22.', '172.23.', '172.24.', '172.25.', '172.26.', '172.27.',
            '172.28.', '172.29.', '172.30.', '172.31.'
        ]
        self._manual_mode = None
        self._load_environment_mode()
        
    def _load_environment_mode(self):
        """加载环境模式配置"""
        env_value = os.getenv('ENVIRONMENT_MODE', '')
        if env_value:
            self._manual_mode = env_value.lower()
            return
        
        try:
            from config import ENVIRONMENT_MODE
            if ENVIRONMENT_MODE:
                self._manual_mode = ENVIRONMENT_MODE.lower()
                return
        except (ImportError, AttributeError):
            pass
        
        self._manual_mode = 'auto'
    
    def get_manual_mode(self):
        """获取手动设置的环境模式"""
        if self._manual_mode is None:
            self._load_environment_mode()
        return self._manual_mode
    
    def is_docker(self):
        if os.path.exists('/.dockerenv'):
            return True
        if os.getenv('DOCKER_CONTAINER', '').lower() == 'true':
            return True
        try:
            with open('/proc/1/cgroup', 'r') as f:
                content = f.read()
                if 'docker' in content or 'containerd' in content:
                    return True
        except:
            pass
        return False
    
    def is_uwsgi(self):
        if os.getenv('UWSGI_MODE', '').lower() == 'true':
            return True
        if 'uwsgi' in os.getenv('SERVER_SOFTWARE', '').lower():
            return True
        try:
            import sys
            if 'uwsgi' in sys.modules:
                return True
        except:
            pass
        return False
    
    def get_run_mode(self):
        is_docker = self.is_docker()
        is_uwsgi = self.is_uwsgi()
        
        if is_docker and is_uwsgi:
            return 'docker-uwsgi'
        elif is_docker:
            return 'docker'
        elif is_uwsgi:
            return 'uwsgi'
        else:
            return 'local'
    
    def is_production(self):
        if os.getenv('FLASK_ENV') == 'production' or os.getenv('ENVIRONMENT') == 'production':
            return True
        
        if self.is_docker() and self.is_uwsgi():
            return True
        
        try:
            hostname = socket.gethostname().lower()
            host_ip = socket.gethostbyname(hostname)
            
            if host_ip in self.local_hosts:
                return False
                
            for prefix in self.private_ip_prefixes:
                if host_ip.startswith(prefix):
                    return False
        except:
            pass
        
        return False
    
    def is_real_production(self):
        """检测是否为真实的生产环境（Docker + uWSGI）"""
        return self.is_docker() and self.is_uwsgi()
    
    def is_manual_production_mode(self):
        """检测是否手动设置为生产模式"""
        return self.get_manual_mode() == 'production'
    
    def is_manual_development_mode(self):
        """检测是否手动设置为测试模式"""
        return self.get_manual_mode() == 'development'
    
    def should_use_production(self):
        """判断应该使用生产环境模式还是测试环境模式"""
        if self.is_real_production():
            return True
        
        if self.is_manual_production_mode():
            return True
        
        if self.is_manual_development_mode():
            return False
        
        if self.is_production():
            return True
        
        return False
    
    def get_environment(self):
        return 'production' if self.should_use_production() else 'development'
    
    def get_environment_mode_info(self):
        """获取环境模式详细信息"""
        info = {
            'is_real_production': self.is_real_production(),
            'is_manual_production': self.is_manual_production_mode(),
            'is_manual_development': self.is_manual_development_mode(),
            'is_auto_production': self.is_production(),
            'manual_mode': self.get_manual_mode(),
            'should_use_production': self.should_use_production()
        }
        return info

env = Environment()

def print_environment_info():
    mode_info = env.get_environment_mode_info()
    
    print("=" * 60)
    print("环境检测信息")
    print("=" * 60)
    print(f"运行环境: {env.get_run_mode()}")
    print(f"环境类型: {env.get_environment()}")
    print(f"Docker模式: {'是' if env.is_docker() else '否'}")
    print(f"uWSGI模式: {'是' if env.is_uwsgi() else '否'}")
    
    print("-" * 60)
    print("环境模式判断:")
    print(f"  [1] 真实生产环境 (Docker+uWSGI): {'是' if mode_info['is_real_production'] else '否'}")
    print(f"  [2] 手动设置生产模式: {'是' if mode_info['is_manual_production'] else '否'}")
    print(f"  [3] 手动设置测试模式: {'是' if mode_info['is_manual_development'] else '否'}")
    print(f"  [4] 自动判断为生产环境: {'是' if mode_info['is_auto_production'] else '否'}")
    print(f"  [5] 当前配置项 ENVIRONMENT_MODE: {mode_info['manual_mode']}")
    print("-" * 60)
    print(f"最终结果: {'生产环境模式' if mode_info['should_use_production'] else '测试环境模式'}")
    print("=" * 60)
    
    try:
        hostname = socket.gethostname()
        host_ip = socket.gethostbyname(hostname)
        print(f"主机名: {hostname}")
        print(f"主机IP: {host_ip}")
    except:
        print(f"主机名: 未知")
        print(f"主机IP: 未知")
    
    print("=" * 60)
