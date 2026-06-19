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
        ('user_id', 'varchar(15)', 'NO', '', None, ''),
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
    'developer_apps': [
        ('id', 'varchar(15)', 'NO', 'PRI', None, ''),
        ('developer_id', 'varchar(15)', 'NO', '', None, ''),
        ('name', 'varchar(100)', 'NO', '', None, ''),
        ('description', 'text', 'YES', '', None, ''),
        ('owner', 'varchar(100)', 'YES', '', None, ''),
        ('website', 'varchar(255)', 'YES', '', None, ''),
        ('app_secret', 'varchar(255)', 'NO', '', None, ''),
        ('status', 'enum', 'NO', '', None, ''),
        ('created_at', 'datetime', 'YES', '', None, ''),
        ('approved_at', 'datetime', 'YES', '', None, '')
    ],
    'developer_authorizations': [
        ('id', 'int', 'NO', 'PRI', None, 'auto_increment'),
        ('app_id', 'varchar(15)', 'NO', '', None, ''),
        ('user_id', 'varchar(15)', 'NO', '', None, ''),
        ('auth_code', 'varchar(30)', 'NO', '', None, ''),
        ('status', 'varchar(20)', 'NO', '', 'active', ''),
        ('permission_restrictions', 'text', 'YES', '', None, ''),
        ('created_at', 'datetime', 'YES', '', None, ''),
        ('expires_at', 'datetime', 'YES', '', None, '')
    ],
    'app_configurations': [
        ('id', 'int', 'NO', 'PRI', None, 'auto_increment'),
        ('app_id', 'varchar(15)', 'NO', 'UNI', None, ''),
        ('login_callback_url', 'varchar(255)', 'YES', '', None, ''),
        ('verification_callback_url', 'varchar(255)', 'YES', '', None, ''),
        ('updated_at', 'datetime', 'YES', '', None, ''),
        ('scope', 'varchar(255)', 'YES', '', None, '')
    ],
    'authorization_log': [
        ('id', 'int', 'NO', 'PRI', None, 'auto_increment'),
        ('user_id', 'varchar(15)', 'NO', '', None, ''),
        ('app_id', 'varchar(15)', 'NO', '', None, ''),
        ('action', 'varchar(50)', 'NO', '', None, ''),
        ('detail', 'text', 'YES', '', None, ''),
        ('ip', 'varchar(45)', 'YES', '', None, ''),
        ('created_at', 'datetime', 'YES', '', None, '')
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
            `user_id` VARCHAR(15) NOT NULL,
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
    'developer_apps': """
        CREATE TABLE developer_apps (
            id VARCHAR(15) PRIMARY KEY,
            developer_id VARCHAR(15) NOT NULL,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            owner VARCHAR(100),
            website VARCHAR(255),
            app_secret VARCHAR(255) NOT NULL,
            status ENUM('pending', 'approved', 'rejected') NOT NULL,
            created_at DATETIME,
            approved_at DATETIME
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    'developer_authorizations': """
        CREATE TABLE developer_authorizations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            app_id VARCHAR(15) NOT NULL,
            user_id VARCHAR(15) NOT NULL,
            auth_code VARCHAR(30) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'active',
            permission_restrictions TEXT,
            created_at DATETIME,
            expires_at DATETIME
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    'app_configurations': """
        CREATE TABLE app_configurations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            app_id VARCHAR(15) NOT NULL UNIQUE,
            login_callback_url VARCHAR(255),
            verification_callback_url VARCHAR(255),
            updated_at DATETIME,
            scope VARCHAR(255)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    'authorization_log': """
        CREATE TABLE authorization_log (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id VARCHAR(15) NOT NULL,
            app_id VARCHAR(15) NOT NULL,
            action VARCHAR(50) NOT NULL,
            detail TEXT,
            ip VARCHAR(45),
            created_at DATETIME
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
                    
                    # 迁移逻辑：为 login_log 表将 user-id 重命名为 user_id
                    if table_name == 'login_log':
                        existing_columns = [col[0] for col in actual_structure]
                        if 'user-id' in existing_columns and 'user_id' not in existing_columns:
                            print(f"为表 '{table_name}' 将 user-id 重命名为 user_id...")
                            cursor.execute("ALTER TABLE login_log CHANGE COLUMN `user-id` `user_id` VARCHAR(15) NOT NULL")
                            print(f"user_id 字段重命名成功")

                    # 迁移逻辑：为 developer_authorizations 表补充缺失字段
                    if table_name == 'developer_authorizations':
                        existing_columns = [col[0] for col in actual_structure]
                        expected_columns = [col[0] for col in expected_structure]
                        
                        if 'status' not in existing_columns:
                            print(f"为表 '{table_name}' 添加 status 字段...")
                            cursor.execute(
                                "ALTER TABLE developer_authorizations "
                                "ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'active'"
                            )
                            print(f"status 字段添加成功")
                        
                        if 'permission_restrictions' not in existing_columns:
                            print(f"为表 '{table_name}' 添加 permission_restrictions 字段...")
                            cursor.execute(
                                "ALTER TABLE developer_authorizations "
                                "ADD COLUMN permission_restrictions TEXT"
                            )
                            print(f"permission_restrictions 字段添加成功")

                    # 迁移逻辑：为 app_configurations 表补充缺失的 scope 字段
                    if table_name == 'app_configurations':
                        existing_columns = [col[0] for col in actual_structure]
                        if 'scope' not in existing_columns:
                            print(f"为表 '{table_name}' 添加 scope 字段...")
                            cursor.execute("ALTER TABLE app_configurations ADD COLUMN scope VARCHAR(255)")
                            print(f"scope 字段添加成功")

                        existing_keys = [col[3] for col in actual_structure]
                        if 'UNI' not in existing_keys:
                            print(f"检测到 app_configurations.app_id 缺少 UNIQUE 约束，正在处理重复数据...")
                            cursor.execute("""
                                DELETE t1 FROM app_configurations t1
                                INNER JOIN app_configurations t2
                                WHERE t1.id < t2.id AND t1.app_id = t2.app_id
                            """)
                            deleted = cursor.rowcount
                            print(f"已删除 {deleted} 条重复记录")
                            cursor.execute(
                                "ALTER TABLE app_configurations ADD UNIQUE INDEX idx_app_id (app_id)"
                            )
                            print(f"app_configurations.app_id UNIQUE 约束添加成功")
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
