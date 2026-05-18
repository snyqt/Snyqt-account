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
        
    def is_production(self):
        if os.getenv('FLASK_ENV') == 'production' or os.getenv('ENVIRONMENT') == 'production':
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
