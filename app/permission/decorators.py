from functools import wraps
from flask import session, jsonify, redirect, request
from app.models.db import get_db_connection


def developer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or not session['logged_in']:
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': '用户未登录'}), 401
            return redirect('/login')

        user_id = session.get('user_id')
        conn = get_db_connection()
        if not conn:
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': '数据库连接失败'}), 500
            return "数据库连接失败", 500

        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM user_permission WHERE user_id = %s AND type = '开发者'", (user_id,))
                if not cursor.fetchone():
                    if request.path.startswith('/api/'):
                        return jsonify({'success': False, 'message': '没有开发者权限'}), 403
                    return redirect('/')
        finally:
            conn.close()

        return f(*args, **kwargs)
    return decorated_function


def check_developer_permission(user_id):
    conn = get_db_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM user_permission WHERE user_id = %s AND type = '开发者'", (user_id,))
            return cursor.fetchone() is not None
    finally:
        conn.close()
