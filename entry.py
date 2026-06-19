# ============================================
# WSGI 入口文件 - uWSGI 启动入口
# ============================================
# 为 uWSGI 提供 `app` 对象
# 用法: uwsgi uwsgi.ini
# ============================================

from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)