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


# 定义每个表的期望结构
EXPECTED_TABLES = {
    'user_info': [
        ('id', 'varchar(15)', 'NO', 'PRI', None, ''),
        ('Name', 'varchar(50)', 'NO', 'UNI', None, ''),
        ('password', 'varchar(64)', 'NO', '', None, ''),
        ('mail', 'varchar(100)', 'YES', '', None, ''),
        ('phone', 'varchar(20)', 'YES', '', None, ''),
        ('avatar', 'varchar(255)', 'YES', '', '/static/img/default_avatar.png', '')
    ],
    'login_log': [
        ('id', 'int', 'NO', 'PRI', None, 'auto_increment'),
        ('user-id', 'varchar(15)', 'NO', '', None, ''),
        ('ip', 'varchar(45)', 'YES', '', None, ''),
        ('time', 'datetime(3)', 'YES', '', None, ''),
        ('is_danger', 'tinyint', 'YES', '', '0', ''),
        ('browser', 'varchar(200)', 'YES', '', None, ''),
        ('is_cookie', 'tinyint', 'YES', '', '0', ''),
        ('place', 'varchar(100)', 'YES', '', None, '')
    ],
    'user_permission': [
        ('id', 'int', 'NO', 'PRI', None, 'auto_increment'),
        ('user_id', 'varchar(15)', 'NO', '', None, ''),
        ('type', 'varchar(50)', 'NO', '', None, '')
    ],
    'user_permission_application': [
        ('id', 'int', 'NO', 'PRI', None, 'auto_increment'),
        ('user_id', 'varchar(15)', 'NO', '', None, ''),
        ('type', 'varchar(50)', 'NO', '', None, ''),
        ('time', 'datetime', 'YES', '', None, '')
    ],
    'email_verification_log': [
        ('id', 'int', 'NO', 'PRI', None, 'auto_increment'),
        ('email', 'varchar(100)', 'NO', '', None, ''),
        ('code', 'varchar(6)', 'NO', '', None, ''),
        ('type', 'varchar(20)', 'NO', '', None, ''),
        ('ip', 'varchar(45)', 'YES', '', None, ''),
        ('time', 'datetime(3)', 'YES', '', None, ''),
        ('status', 'varchar(20)', 'NO', '', None, ''),
        ('error_msg', 'varchar(255)', 'YES', '', None, '')
    ]
}

# 每个表的创建SQL
CREATE_TABLE_SQLS = {
    'user_info': """
        CREATE TABLE user_info (
            id VARCHAR(15) PRIMARY KEY,
            Name VARCHAR(50) UNIQUE NOT NULL,
            password VARCHAR(64) NOT NULL,
            mail VARCHAR(100),
            phone VARCHAR(20),
            avatar VARCHAR(255) DEFAULT '/static/img/default_avatar.png'
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    'login_log': """
        CREATE TABLE login_log (
            id INT AUTO_INCREMENT PRIMARY KEY,
            `user-id` VARCHAR(15) NOT NULL,
            ip VARCHAR(45),
            time DATETIME(3),
            is_danger TINYINT DEFAULT 0,
            browser VARCHAR(200),
            is_cookie TINYINT DEFAULT 0,
            place VARCHAR(100)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    'user_permission': """
        CREATE TABLE user_permission (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id VARCHAR(15) NOT NULL,
            type VARCHAR(50) NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    'user_permission_application': """
        CREATE TABLE user_permission_application (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id VARCHAR(15) NOT NULL,
            type VARCHAR(50) NOT NULL,
            time DATETIME
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    'email_verification_log': """
        CREATE TABLE email_verification_log (
            id INT AUTO_INCREMENT PRIMARY KEY,
            email VARCHAR(100) NOT NULL,
            code VARCHAR(6) NOT NULL,
            type VARCHAR(20) NOT NULL,
            ip VARCHAR(45),
            time DATETIME(3),
            status VARCHAR(20) NOT NULL,
            error_msg VARCHAR(255)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """
}


def get_table_structure(conn, table_name):
    """获取指定表的结构信息"""
    try:
        cursor = conn.cursor()
        cursor.execute(f"SHOW COLUMNS FROM {table_name}")
        cols = cursor.fetchall()
        cursor.close()
        return cols
    except Exception as e:
        return None


def compare_table_structure(actual, expected):
    """比较表结构是否匹配"""
    if len(actual) != len(expected):
        return False
    
    for i in range(len(actual)):
        # 比较字段名、类型、是否为空、键类型
        if (actual[i][0] != expected[i][0] or
            not actual[i][1].lower().startswith(expected[i][1].lower())):
            return False
    
    return True


def check_and_create_tables():
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            print("数据库连接失败，无法检查表结构")
            return
        
        cursor = conn.cursor()
        
        # 获取所有已存在的表
        cursor.execute("SHOW TABLES")
        existing_tables = {row[0] for row in cursor.fetchall()}
        
        for table_name in EXPECTED_TABLES.keys():
            print(f"正在检查表 '{table_name}'...")
            
            if table_name not in existing_tables:
                print(f"表 '{table_name}' 不存在，正在创建...")
                cursor.execute(CREATE_TABLE_SQLS[table_name])
                print(f"表 '{table_name}' 创建成功")
            else:
                # 检查表结构
                actual_structure = get_table_structure(conn, table_name)
                expected_structure = EXPECTED_TABLES[table_name]
                
                if not compare_table_structure(actual_structure, expected_structure):
                    print(f"表 '{table_name}' 结构不匹配！")
                    print(f"期望结构: {expected_structure}")
                    print(f"实际结构: {actual_structure}")
                else:
                    print(f"表 '{table_name}' 结构正确")
        
        conn.commit()
        cursor.close()
        conn.close()
        print("数据库表检查完成")
    except Exception as e:
        print(f"数据库表检查失败: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            try:
                conn.close()
            except:
                pass
