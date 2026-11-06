from app import create_app
from app.env_config import auto_configure

app = create_app()

if __name__ == '__main__':
    config = auto_configure()
    
    port = config['port']
    debug = config['debug']
    environment = config['environment']
    
    app.run(host='0.0.0.0', port=port, debug=debug)
