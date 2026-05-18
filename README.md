# SNYQT 统一账户认证系统

一个基于 Flask 的统一账户认证系统，提供用户认证、权限控制、登录安全等完整的账户管理功能。

## 功能特性

### 用户认证与安全
- 用户注册 / 登录 / 忘记密码
- 邮箱验证码 & 短信验证码（阿里云短信服务）
- Cloudflare Turnstile 人机验证
- 登录风控检测（异地登录、新设备检测、失败次数阈值）
- 二次验证（2FA）：风险登录触发邮箱 + 手机双重验证
- 记住我功能（7天免登录）
- SHA-256 密码哈希

### 用户管理
- 个人信息查看与编辑（用户名、邮箱、手机号、头像）
- 密码修改（旧密码验证 + 新密码强度检查）
- 头像上传与裁剪（PIL 图片处理）
- 管理员用户信息管理（查看、修改所有用户信息）

### 用户界面
- 深色/浅色主题切换（自动记住用户偏好）
- 现代化渐变配色（基于Logo色彩的品牌设计）
- 响应式设计，支持移动设备
- 流畅的动画过渡效果
- 首页功能卡片导航

### 权限管理
- 简化二级权限体系：管理员、普通用户
- 权限申请与审批流程
- 批量审批功能
- 管理员拥有所有管理权限

### 登录日志
- 用户个人登录记录查询
- 管理员全局登录日志查询（支持按用户 / 时间 / IP 筛选）
- 浏览器与设备信息记录
- IP 地理位置记录

### 邮箱验证码日志
- 完整记录所有邮箱验证码发送事件（注册、2FA等）
- 记录验证码内容、发送状态、失败原因
- 记录请求IP地址和精确时间戳
- 支持按邮箱、类型、状态筛选查询

## 技术栈

| 类别 | 技术 |
|------|------|
| **后端框架** | Flask 2.3.3 |
| **数据库** | MySQL (PyMySQL 1.1.0) |
| **图片处理** | Pillow 12.1.1 |
| **短信服务** | 阿里云短信 (alibabacloud_dypnsapi20170525) |
| **人机验证** | Cloudflare Turnstile |
| **前端** | HTML5 / CSS3 / JavaScript |
| **图标** | Font Awesome 6 |
| **部署** | Docker + uWSGI |
| **Python** | 3.11 |

## 项目结构

```
Snyqt-account/
├── run.py                          # 应用入口
├── config.example.py               # 配置文件模板
├── requirements.txt                # Python 依赖
├── Dockerfile                      # Docker 部署配置
├── LICENSE                         # MIT 开源协议
├── .gitignore                      # Git 忽略规则
├── app/                            # 应用模块
│   ├── __init__.py                 # 应用工厂（创建 Flask 实例、注册蓝图）
│   ├── models/                     # 数据模型
│   │   ├── __init__.py
│   │   └── db.py                   # 数据库连接与表自检
│   ├── auth/                       # 认证模块
│   │   ├── __init__.py
│   │   ├── routes.py               # 认证路由（登录/注册/忘记密码/2FA/验证码）
│   │   └── utils.py                # 认证工具（密码哈希/验证码/Turnstile/风控/邮件/短信）
│   ├── user/                       # 用户模块
│   │   ├── __init__.py
│   │   ├── routes.py               # 用户路由（个人信息/头像/密码修改）
│   │   └── utils.py                # 用户工具（头像路径获取）
│   ├── admin/                      # 管理员模块
│   │   ├── __init__.py
│   │   ├── routes.py               # 管理员路由（用户管理/权限管理/登录日志）
│   │   └── utils.py                # 管理员工具（头像路径获取）
│   ├── permission/                 # 权限模块
│   │   ├── __init__.py
│   │   ├── routes.py               # 权限路由（权限申请/审批/删除）
│   │   └── utils.py                # 权限工具（权限检查辅助函数）
│   └── templates/                  # HTML 模板
│       ├── index.html              # 首页
│       ├── login.html              # 登录 / 注册
│       ├── forgot_password.html    # 忘记密码
│       ├── profile.html            # 个人信息
│       ├── permission.html         # 权限申请
│       ├── user_permission_management.html  # 权限管理
│       ├── user_info_management.html        # 用户信息管理
│       ├── admin_login_log.html             # 管理员登录日志
│       ├── user_login_log.html              # 用户登录日志
│       ├── 401.html                # 401 未授权
│       ├── 403.html                # 403 禁止访问
│       ├── 404.html                # 404 页面未找到
│       └── 500.html                # 500 服务器错误
└── static/                         # 静态资源
    ├── img/                        # 图片资源
    │   ├── logo.png                # 系统 Logo
    │   └── user_avatar/            # 用户头像
    └── css/
        └── icon/                   # Font Awesome 图标库
```

## 数据库设计

系统使用 MySQL 数据库，启动时自动检测并创建缺失的表。包含以下 5 张核心表：

| 表名 | 说明 |
|------|------|
| `user_info` | 用户信息（用户名、密码、邮箱、手机号） |
| `login_log` | 登录日志（IP、时间、浏览器、地理位置、风险标记） |
| `user_permission` | 用户权限（用户ID、权限类型） |
| `user_permission_application` | 权限申请记录 |
| `email_verification_log` | 邮箱验证码发送日志（邮箱、验证码、类型、状态、IP、时间） |

## 快速开始

### 前置条件

- Python 3.11+
- MySQL 5.7+
- 阿里云短信服务账号（可选）
- Cloudflare Turnstile 密钥（可选）

### 本地开发

1. **克隆仓库**

```bash
git clone https://github.com/snyqt/Snyqt-account.git
cd Snyqt-account
```

2. **创建虚拟环境并安装依赖**

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

pip install -r requirements.txt
```

3. **配置项目**

```bash
cp config.example.py config.py
```

编辑 `config.py`，填入你的配置信息：

```python
# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'your_db_user',
    'password': 'your_db_password',
    'database': 'Snyqt-account-sql',
}

# Flask 密钥（务必修改！）
SECRET_KEY = 'your-random-secret-key'

# 邮箱 SMTP 配置
EMAIL_CONFIG = {
    'smtp_server': 'smtp.qq.com',
    'port': 587,
    'sender': 'your-email@qq.com',
    'password': 'your-email-auth-code',
}
```

4. **初始化数据库**

创建 MySQL 数据库：

```sql
CREATE DATABASE `Snyqt-account-sql` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

应用启动时会自动检测并创建所需的表，无需手动导入 SQL 文件。

5. **启动应用**

```bash
python run.py
```

应用将在 `http://localhost:80` 启动。

### Docker 部署

1. **构建镜像**

```bash
docker build -t snyqt-account .
```

2. **运行容器**

```bash
docker run -d \
  -p 80:80 \
  -e DB_HOST=your_db_host \
  -e DB_USER=your_db_user \
  -e DB_PASSWORD=your_db_password \
  -e DB_NAME=Snyqt-account-sql \
  -e SECRET_KEY=your-secret-key \
  -e EMAIL_SENDER=your-email@qq.com \
  -e EMAIL_PASSWORD=your-email-auth-code \
  --name snyqt-account \
  snyqt-account
```

应用将在 `http://localhost` 启动（uWSGI 模式，自动启用 Cloudflare Turnstile）。

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DB_HOST` | 数据库主机 | `localhost` |
| `DB_USER` | 数据库用户 | - |
| `DB_PASSWORD` | 数据库密码 | - |
| `DB_NAME` | 数据库名称 | `Snyqt-account-sql` |
| `SECRET_KEY` | Flask 密钥 | - |
| `SMTP_SERVER` | SMTP 服务器 | `smtp.qq.com` |
| `SMTP_PORT` | SMTP 端口 | `587` |
| `EMAIL_SENDER` | 发件人邮箱 | - |
| `EMAIL_PASSWORD` | 邮箱授权码 | - |
| `ALIYUN_ACCESS_KEY_ID` | 阿里云 AccessKey ID | - |
| `ALIYUN_ACCESS_KEY_SECRET` | 阿里云 AccessKey Secret | - |
| `ALIYUN_SIGN_NAME` | 短信签名 | - |
| `ALIYUN_TEMPLATE_CODE` | 短信模板 CODE | - |
| `TURNSTILE_SECRET_KEY` | Turnstile 密钥 | - |
| `TURNSTILE_SITEKEY` | Turnstile 站点密钥 | - |
| `TURNSTILE_ENABLED` | 是否启用 Turnstile | `False` |
| `ENABLE_2FA` | 是否强制启用二次验证 | `False` |
| `RISK_CONTROL_ENABLED` | 是否启用风控 | `True` |
| `VERIFICATION_CODE_EXPIRE` | 验证码有效期（秒） | `300` |
| `REMEMBER_ME_COOKIE_DURATION` | 记住我天数 | `7` |
| `SESSION_DURATION` | 会话时长（分钟） | `10` |

## 权限体系

系统采用简化的二级权限管理：

```
管理员
  └── 可管理所有权限、用户信息、登录日志、审批权限申请

普通用户
  └── 可管理自己的信息、申请权限
```

## API 概览

| 模块 | 端点数 | 说明 |
|------|--------|------|
| 认证相关 | 15 | 登录、注册、验证码、2FA、密码重置 |
| 用户信息 | 12 | 个人信息查询与修改 |
| 权限管理 | 12 | 权限申请、审批、删除 |
| 管理员 | 11 | 用户管理、登录日志管理 |
| 登录日志 | 2 | 用户 & 管理员日志查询 |

## 开源协议

本项目基于 [MIT License](LICENSE) 开源。

Copyright © 2026 少年友晴天
