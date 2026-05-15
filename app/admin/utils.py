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
