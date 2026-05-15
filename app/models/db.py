import pymysql
from config import DB_CONFIG


def get_db_connection():
    try:
        config = DB_CONFIG.copy()
        config['charset'] = 'utf8mb4'
        conn = pymysql.connect(**config)
        return conn
    except Exception as e:
        print(f"数据库连接失败: {e}")
        return None


def check_and_create_tables():
    tables = {
        'user_info': """
            CREATE TABLE IF NOT EXISTS user_info (
                id INT AUTO_INCREMENT PRIMARY KEY,
                Name VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(64) NOT NULL,
                mail VARCHAR(100),
                phone VARCHAR(20)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        'login_log': """
            CREATE TABLE IF NOT EXISTS login_log (
                id INT AUTO_INCREMENT PRIMARY KEY,
                `user-id` INT NOT NULL,
                ip VARCHAR(45),
                time DATETIME(3),
                is_danger TINYINT DEFAULT 0,
                browser VARCHAR(200),
                is_cookie TINYINT DEFAULT 0,
                place VARCHAR(100)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        'user_permission': """
            CREATE TABLE IF NOT EXISTS user_permission (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                type VARCHAR(50) NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """,
        'user_permission_application': """
            CREATE TABLE IF NOT EXISTS user_permission_application (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                type VARCHAR(50) NOT NULL,
                time DATETIME
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    }

    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            print("数据库连接失败，无法检查表结构")
            return
        cursor = conn.cursor()
        for table_name, create_sql in tables.items():
            cursor.execute("SHOW TABLES LIKE %s", (table_name,))
            result = cursor.fetchone()
            if result:
                print(f"表 '{table_name}' 已存在")
            else:
                cursor.execute(create_sql)
                print(f"表 '{table_name}' 创建成功")
        conn.commit()
        cursor.close()
        conn.close()
        print("数据库表自检完成")
    except Exception as e:
        print(f"数据库表自检失败: {e}")
        if conn:
            try:
                conn.close()
            except:
                pass
