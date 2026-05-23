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

    def get_environment(self):
        return 'production' if self.is_production() else 'development'

env = Environment()

def print_environment_info():
    print("=" * 50)
    print("环境检测信息")
    print("=" * 50)
    print(f"运行环境: {env.get_run_mode()}")
    print(f"环境类型: {env.get_environment()}")
    print(f"Docker模式: {'是' if env.is_docker() else '否'}")
    print(f"uWSGI模式: {'是' if env.is_uwsgi() else '否'}")
    print(f"生产环境: {'是' if env.is_production() else '否'}")
    
    try:
        hostname = socket.gethostname()
        host_ip = socket.gethostbyname(hostname)
        print(f"主机名: {hostname}")
        print(f"主机IP: {host_ip}")
    except:
        print(f"主机名: 未知")
        print(f"主机IP: 未知")
    
    print("=" * 50)
