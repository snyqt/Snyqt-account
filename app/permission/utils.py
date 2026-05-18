import os
from flask import current_app
from app.models.db import get_db_connection

avatar_extensions = ['png', 'jpg', 'jpeg', 'gif']

def get_user_avatar_path(user_id):
    avatar_path = '/static/img/default_avatar.png'
    for ext in avatar_extensions:
        potential_path = f"static/img/user_avatar/{user_id}.{ext}"
        if os.path.exists(os.path.join(current_app.config['PROJECT_ROOT'], potential_path)):
            avatar_path = f"/static/img/user_avatar/{user_id}.{ext}"
            break
    return avatar_path

def is_admin(user_id):
    conn = get_db_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM user_permission WHERE user_id = %s AND type = '管理员'", (user_id,))
            return cursor.fetchone() is not None
    finally:
        conn.close()

def can_approve_permission(operator_id, permission_type):
    if is_admin(operator_id):
        return True
    return False
