<div align="center">
  <img src="static/img/logo.png" alt="SNYQT Logo" width="120" height="120" style="border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">

# 少年友晴天 - 统一账户认证系统

  <p>
    <strong>一个功能完善的统一账户认证与OAuth授权平台</strong>
  </p>

  <p>
    <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python">
    <img src="https://img.shields.io/badge/Flask-2.3.3-green.svg" alt="Flask">
    <img src="https://img.shields.io/badge/MySQL-5.7+-orange.svg" alt="MySQL">
    <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
  </p>

  <p>
    <a href="https://snyqt-account.iepose.cn">在线演示 </a> •
    <a href="#-快速开始">快速开始</a> •
    <a href="#-开发者平台oauth-20">开发者平台OAuth</a> •
    <a href="#-联系方式">联系方式</a>
  </p>
</div>

***

## 📋 目录

- [功能特性](#-功能特性)
- [技术栈](#-技术栈)
- [项目结构](#-项目结构)
- [快速开始](#-快速开始)
  - [前置条件](#前置条件)
  - [本地开发](#本地开发)
  - [Docker部署](#docker部署)
- [环境变量](#-环境变量)
- [API文档](#-api文档)
  - [认证相关API](#认证相关api)
  - [OAuth授权API](#oauth授权api)
  - [用户管理API](#用户管理api)
  - [管理员API](#管理员api)
- [数据库设计](#-数据库设计)
- [权限体系](#-权限体系)
- [联系方式](#-联系方式)
- [贡献指南](#-贡献指南)
- [更新日志](#-更新日志)
- [开源协议](#-开源协议)

***

## ✨ 功能特性

### 🔐 用户认证与安全

- ✅ 用户注册 / 登录 / 忘记密码
- ✅ 邮箱验证码 & 短信验证码（阿里云短信服务）
- ✅ Cloudflare Turnstile 人机验证
- ✅ Cloudflare Turnstile 全局验证中间件（生产环境自动启用，除 /developer-docs）
- ✅ 登录风控检测（异地登录、新设备检测、失败次数阈值）
- ✅ 二次验证（2FA）：风险登录触发邮箱 + 手机双重验证
- ✅ 记住我功能（7天免登录）
- ✅ SHA-256 密码哈希
- ✅ 会话管理（10分钟自动过期）

### 👤 用户管理

- ✅ 个人信息查看与编辑（用户名、邮箱、手机号、头像）
- ✅ 密码修改（旧密码验证 + 新密码强度检查）
- ✅ 头像上传与裁剪（PIL 图片处理）
- ✅ 管理员用户信息管理（查看、修改所有用户信息）
- ✅ 用户头像管理

### 🎨 用户界面

- 🌙 深色/浅色主题切换（自动记住用户偏好）
- 🎨 现代化渐变配色（基于Logo色彩的品牌设计）
- 📱 响应式设计，支持移动设备
- ✨ 流畅的动画过渡效果
- 🏠 首页功能卡片导航

### 🔑 权限管理

- 👥 简化二级权限体系：管理员、普通用户、开发者
- 📝 权限申请与审批流程
- 📋 批量审批功能
- 🛡️ 管理员拥有所有管理权限

### 🚀 开发者平台（OAuth 2.0）

- 📱 OAuth 2.0 授权流程
- 📦 第三方应用创建与管理
- ✔️ 应用审核与审批（生成 App ID 和 App Secret）
- 🔌 Account API（获取用户信息：用户名、头像、ID）
- ✉️ 验证码 API（支持邮箱/手机验证码发送）
- 🔄 登录回调与验证码回调机制
- ⚙️ 应用配置管理（回调地址设置）
- 🔑 Scope 权限范围配置（基本信息/邮箱验证码/手机验证码）

### 📊 登录日志

- 📜 用户个人登录记录查询
- 🔍 管理员全局登录日志查询（支持按用户 / 时间 / IP 筛选）
- 🌐 浏览器与设备信息记录
- 📍 IP 地理位置记录

### 🛡️ 第三方安全管理

- 📋 已授权应用列表查看（授权时间、权限范围）
- 🚫 取消应用授权（拉黑机制）
- 🔒 精细化权限控制（禁止发送邮件/手机验证码/访问个人信息）
- 📝 授权操作日志（操作人、操作类型、详情、IP、时间）

***

## 🛠 技术栈

| 类别         | 技术                                     |
| ---------- | -------------------------------------- |
| **后端框架**   | Flask 2.3.3                            |
| **数据库**    | MySQL 5.7+ (PyMySQL 1.1.0)             |
| **图片处理**   | Pillow 12.1.1                          |
| **短信服务**   | 阿里云短信 (alibabacloud\_dypnsapi20170525) |
| **人机验证**   | Cloudflare Turnstile                   |
| **前端**     | HTML5 / CSS3 / JavaScript (原生)         |
| **图标**     | Font Awesome 6                         |
| **部署**     | Docker + uWSGI / 直接运行                  |
| **OAuth**  | OAuth 2.0                              |
| **Python** | 3.11+                                  |

***

## 📁 项目结构

```
Snyqt-account/
├── run.py                          # 应用入口文件
├── config.example.py               # 配置文件模板
├── config.py                       # 实际配置文件（需创建）
├── requirements.txt                # Python 依赖列表
├── Dockerfile                      # Docker 部署配置
├── uwsgi.ini                       # uWSGI 配置文件
├── LICENSE                         # MIT 开源协议
├── README.md                       # 项目说明文档
├── .gitignore                      # Git 忽略规则
│
├── app/                            # 应用主目录
│   ├── __init__.py                 # 应用工厂（Flask 实例创建、蓝图注册）
│   ├── env.py                      # 环境变量加载
│   ├── env_config.py               # 环境配置
│   │
│   ├── models/                     # 数据模型
│   │   ├── __init__.py
│   │   └── db.py                   # 数据库连接、表创建与验证
│   │
│   ├── auth/                       # 认证模块
│   │   ├── __init__.py
│   │   ├── routes.py               # 认证路由（登录/注册/验证码/2FA）
│   │   └── utils.py                # 认证工具（密码哈希/邮件/短信/风控）
│   │
│   ├── user/                       # 用户模块
│   │   ├── __init__.py
│   │   ├── routes.py               # 用户路由（个人信息/头像/密码）
│   │   └── utils.py                # 用户工具函数
│   │
│   ├── admin/                      # 管理员模块
│   │   ├── __init__.py
│   │   ├── routes.py               # 管理员路由（用户/权限/日志管理）
│   │   └── utils.py                # 管理员工具函数
│   │
│   ├── permission/                 # 权限模块
│   │   ├── __init__.py
│   │   ├── routes.py               # 权限路由（申请/审批/删除）
│   │   ├── utils.py                # 权限检查工具
│   │   └── decorators.py           # 权限装饰器
│   │
│   ├── developer/                  # 开发者模块
│   │   ├── __init__.py
│   │   └── routes.py               # 开发者路由（应用管理/OAuth API）
│   │
│   ├── security/                   # 第三方安全管理模块
│   │   ├── __init__.py             # 安全蓝图定义
│   │   └── routes.py               # 第三方安全管理路由
│   │
│   └── templates/                  # HTML 模板
│       ├── index.html               # 首页
│       ├── login.html               # 登录/注册页
│       ├── forgot_password.html      # 忘记密码页
│       ├── profile.html              # 个人信息页
│       ├── permission.html           # 权限申请页
│       ├── app_management.html       # 管理员应用管理
│       ├── app_review.html           # 应用审核页
│       ├── developer_app_management.html  # 开发者应用管理
│       ├── developer_docs.html       # 开发者文档
│       ├── oauth_authorize.html     # OAuth 授权确认页
│       ├── third_party_security.html # 第三方安全管理页
│       ├── user_info_management.html # 用户信息管理（管理员）
│       ├── user_permission_management.html  # 权限管理（管理员）
│       ├── user_login_log.html      # 用户登录日志
│       ├── admin_login_log.html     # 管理员登录日志
│       ├── 401.html                 # 401 未授权页面
│       ├── 403.html                 # 403 禁止访问页面
│       ├── 404.html                 # 404 页面未找到
│       └── 500.html                 # 500 服务器错误页面
│
└── static/                         # 静态资源目录
    ├── img/                        # 图片资源
    │   ├── logo.png               # 系统 Logo
    │   ├── default_avatar.png     # 默认头像
    │   ├── default_avatar.svg     # 默认头像（SVG）
    │   ├── class_avatar/           # 预设头像分类
    │   └── user_avatar/           # 用户上传头像存储
    │
    ├── css/                       # 样式文件
    │   ├── common.css             # 通用样式
    │   ├── theme-toggle.css       # 主题切换样式
    │   └── icon/                  # Font Awesome 图标库
    │       ├── css/               # CSS 文件
    │       ├── js/                # JS 文件
    │       └── webfonts/          # 字体文件
    │
    └── js/                        # JavaScript 文件
        └── theme-toggle.js         # 主题切换脚本
```

***

## 🚀 快速开始

### 前置条件

| 软件                   | 版本要求  | 说明      |
| -------------------- | ----- | ------- |
| Python               | 3.11+ | 运行环境    |
| MySQL                | 5.7+  | 数据库     |
| 阿里云短信                | 可选    | 短信验证码服务 |
| Cloudflare Turnstile | 可选    | 人机验证    |

### 本地开发

#### 1. 克隆仓库

```bash
git clone https://github.com/snyqt/Snyqt-account.git
cd Snyqt-account
```

#### 2. 创建虚拟环境并安装依赖

```bash
# 创建虚拟环境
python -m venv venv

# Windows 激活
venv\Scripts\activate

# Linux/macOS 激活
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

#### 3. 配置项目

```bash
# 复制配置文件
copy config.example.py config.py
```

编辑 `config.py`，填入你的配置信息：

```python
# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'your_db_user',
    'password': 'your_db_password',
    'database': 'Snyqt-account',
}

# Flask 密钥（务必修改！）
SECRET_KEY = 'your-random-secret-key-here'

# 邮箱 SMTP 配置
EMAIL_CONFIG = {
    'smtp_server': 'smtp.qq.com',
    'port': 587,
    'sender': 'your-email@qq.com',
    'password': 'your-email-auth-code'
}

# 阿里云短信配置（可选）
ALIYUN_SMS_CONFIG = {
    'access_key_id': 'your-access-key-id',
    'access_key_secret': 'your-access-key-secret',
    'sign_name': '您的短信签名',
    'template_code': 'SMS_XXXXXXX',
}
```

#### 4. 初始化数据库

登录 MySQL 并创建数据库：

```sql
CREATE DATABASE `Snyqt-account` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

> 💡 应用启动时会自动检测并创建所需的表结构，无需手动导入 SQL 文件。

#### 5. 启动应用

```bash
python run.py
```

应用将在 `http://localhost:5000` 启动。按 `Ctrl+C` 停止服务。

### Docker 部署

#### 1. 构建镜像

```bash
docker build -t snyqt-account .
```

#### 2. 运行容器

```bash
docker run -d \
  --name snyqt-account \
  -p 5000:5000 \
  -e DB_HOST=your_db_host \
  -e DB_USER=your_db_user \
  -e DB_PASSWORD=your_db_password \
  -e DB_NAME=Snyqt-account \
  -e SECRET_KEY=your-secret-key \
  -e SMTP_SERVER=smtp.qq.com \
  -e SMTP_PORT=587 \
  -e SMTP_SENDER=your-email@qq.com \
  -e SMTP_PASSWORD=your-email-auth-code \
  snyqt-account
```

#### 3. 使用 Docker Compose（推荐）

创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - DB_HOST=db
      - DB_USER=your_db_user
      - DB_PASSWORD=your_db_password
      - DB_NAME=Snyqt-account
      - SECRET_KEY=your-secret-key
    depends_on:
      - db

  db:
    image: mysql:5.7
    environment:
      - MYSQL_ROOT_PASSWORD=root_password
      - MYSQL_DATABASE=Snyqt-account
      - MYSQL_USER=your_db_user
      - MYSQL_PASSWORD=your_db_password
    volumes:
      - mysql_data:/var/lib/mysql

volumes:
  mysql_data:
```

启动服务：

```bash
docker-compose up -d
```

***

## 🔧 环境变量

| 变量名                           | 说明                               | 必需 | 默认值             |
| ----------------------------- | -------------------------------- | -- | --------------- |
| `DB_HOST`                     | 数据库主机地址                          | ✅  | `localhost`     |
| `DB_USER`                     | 数据库用户名                           | ✅  | -               |
| `DB_PASSWORD`                 | 数据库密码                            | ✅  | -               |
| `DB_NAME`                     | 数据库名称                            | ✅  | `Snyqt-account` |
| `SECRET_KEY`                  | Flask 密钥                         | ✅  | -               |
| `SMTP_SERVER`                 | SMTP 服务器                         | ✅  | `smtp.qq.com`   |
| `SMTP_PORT`                   | SMTP 端口                          | ❌  | `587`           |
| `SMTP_SENDER`                 | 发件人邮箱                            | ✅  | -               |
| `SMTP_PASSWORD`               | 邮箱授权码                            | ✅  | -               |
| `ALIYUN_ACCESS_KEY_ID`        | 阿里云 AccessKey ID                 | ❌  | -               |
| `ALIYUN_ACCESS_KEY_SECRET`    | 阿里云 AccessKey Secret             | ❌  | -               |
| `ALIYUN_SIGN_NAME`            | 短信签名                             | ❌  | -               |
| `ALIYUN_TEMPLATE_CODE`        | 短信模板 CODE                        | ❌  | -               |
| `TURNSTILE_SECRET_KEY`        | Turnstile 密钥                     | ❌  | -               |
| `TURNSTILE_SITEKEY`           | Turnstile 站点密钥                   | ❌  | -               |
| `TURNSTILE_ENABLED`           | 是否启用全局 Turnstile 验证（留空则生产环境自动启用） | ❌  | `自动`            |
| `ENABLE_2FA`                  | 是否启用二次验证                         | ❌  | `False`         |
| `RISK_CONTROL_ENABLED`        | 是否启用风控                           | ❌  | `True`          |
| `VERIFICATION_CODE_EXPIRE`    | 验证码有效期（秒）                        | ❌  | `300`           |
| `REMEMBER_ME_COOKIE_DURATION` | 记住我天数                            | ❌  | `7`             |
| `SESSION_DURATION`            | 会话时长（分钟）                         | ❌  | `10`            |

***

## 📖 API文档

### 认证相关API

| 方法   | 端点                     | 说明       |
| ---- | ---------------------- | -------- |
| POST | `/login`               | 用户登录     |
| POST | `/register`            | 用户注册     |
| POST | `/logout`              | 用户登出     |
| POST | `/send_code`           | 发送邮箱验证码  |
| POST | `/verify_code`         | 验证邮箱验证码  |
| POST | `/forgot_password`     | 忘记密码     |
| GET  | `/forgot_password`     | 获取忘记密码页面 |
| POST | `/api/send-sms-code`   | 发送短信验证码  |
| POST | `/api/verify-sms-code` | 验证短信验证码  |

### OAuth授权API

| 方法   | 端点                             | 说明         |
| ---- | ------------------------------ | ---------- |
| GET  | `/oauth/authorize`             | OAuth 授权入口 |
| POST | `/oauth/authorize/confirm`     | 确认授权       |
| POST | `/api/oauth/userinfo`          | 获取用户信息     |
| POST | `/api/oauth/send-verification` | 发送验证码      |

### OAuth授权流程

```
1. 用户访问第三方应用
2. 应用重定向到授权页面:
   GET /oauth/authorize?app_id=xxx&redirect_uri=xxx

3. 用户确认授权:
   POST /oauth/authorize/confirm
   {
     "app_id": "xxx",
     "redirect_uri": "xxx"
   }

4. 获取授权码 (auth_code)，有效期1天

5. 使用授权码换取用户信息:
   POST /api/oauth/userinfo
   {
     "app_id": "xxx",
     "app_secret": "xxx",
     "auth_code": "xxx"
   }
```

### 第三方安全管理API

#### 获取已授权应用列表

- **URL**: `/api/third-party-security`
- **Method**: `GET`
- **Headers**: `Cookie: session=xxx`（需登录）
- **Query Params**: `status`（可选，`active`/`blacklisted`）
- **Success Response**: `{ "success": true, "authorizations": [...] }`

#### 取消应用授权（不拉黑）

- **URL**: `/api/third-party/cancel-auth`
- **Method**: `POST`
- **Content-Type**: `application/json`
- **Body**: `{ "app_id": "xxx", "auth_id": 1 }`
- **Success Response**: `{ "success": true, "message": "已取消授权" }`

#### 拉黑应用

- **URL**: `/api/third-party/blacklist-app`
- **Method**: `POST`
- **Content-Type**: `application/json`
- **Body**: `{ "app_id": "xxx", "auth_id": 1 }`
- **Success Response**: `{ "success": true, "message": "已将应用加入黑名单" }`

#### 解除黑名单

- **URL**: `/api/third-party/restore-auth`
- **Method**: `POST`
- **Content-Type**: `application/json`
- **Body**: `{ "app_id": "xxx", "auth_id": 1 }`
- **Success Response**: `{ "success": true, "message": "已解除黑名单" }`

#### 设置权限限制

- **URL**: `/api/third-party/restrict-permission`
- **Method**: `POST`
- **Content-Type**: `application/json`
- **Body**: `{ "app_id": "xxx", "auth_id": 1, "permission_type": "no_email", "enabled": true }`
- **Success Response**: `{ "success": true }`

#### 获取授权日志

- **URL**: `/api/authorization-log`
- **Method**: `GET`
- **Query Params**: `search`（可选，搜索应用名称或操作类型）
- **Success Response**: `{ "success": true, "logs": [...] }`

### 用户管理API

| 方法   | 端点                          | 说明      |
| ---- | --------------------------- | ------- |
| GET  | `/profile`                  | 获取个人信息页 |
| POST | `/api/update-profile`       | 更新个人信息  |
| POST | `/api/update-avatar`        | 更新头像    |
| POST | `/api/change-password`      | 修改密码    |
| GET  | `/api/user-info`            | 获取用户信息  |
| GET  | `/api/get-user-permissions` | 获取用户权限  |

### 开发者API

| 方法     | 端点                                   | 说明            |
| ------ | ------------------------------------ | ------------- |
| GET    | `/developer-docs`                    | 开发者文档页        |
| GET    | `/developer-app-management`          | 开发者应用管理页      |
| POST   | `/api/developer/create-app`          | 创建应用          |
| GET    | `/api/developer/apps`                | 获取应用列表        |
| DELETE | `/api/developer/delete-app`          | 删除应用          |
| POST   | `/api/developer/configure-callback`  | 配置回调地址和 Scope |
| GET    | `/api/developer/app-secret/<app_id>` | 获取 App Secret |
| GET    | `/api/developer/app-config/<app_id>` | 获取应用配置        |

#### Scope 权限范围

应用配置时可设置 scope 权限范围，支持以下选项：

| scope 值      | 说明                         |
| ------------ | -------------------------- |
| `userinfo`   | 获取用户基本信息（用户ID、用户名、头像），默认必选 |
| `email_code` | 允许向用户邮箱发送验证码               |
| `phone_code` | 允许向用户手机发送验证码               |

配置回调时 scope 格式为数组，例如：

```json
{
  "scope": ["userinfo", "email_code"]
}
```

### 管理员API

| 方法     | 端点                        | 说明       |
| ------ | ------------------------- | -------- |
| GET    | `/admin/users`            | 用户信息管理页  |
| GET    | `/admin/login-log`        | 管理员登录日志页 |
| GET    | `/admin/user-login-log`   | 用户登录日志页  |
| GET    | `/admin/app-review`       | 应用审核页    |
| GET    | `/admin/app-management`   | 应用管理页    |
| GET    | `/api/admin/users`        | 获取用户列表   |
| POST   | `/api/admin/update-user`  | 更新用户信息   |
| POST   | `/api/admin/delete-user`  | 删除用户     |
| GET    | `/api/admin/pending-apps` | 获取待审核应用  |
| POST   | `/api/admin/approve-app`  | 审批通过应用   |
| POST   | `/api/admin/reject-app`   | 拒绝应用     |
| GET    | `/api/admin/all-apps`     | 获取所有应用   |
| POST   | `/api/admin/update-app`   | 更新应用信息   |
| DELETE | `/api/admin/delete-app`   | 删除应用     |

### 权限管理API

| 方法   | 端点                              | 说明       |
| ---- | ------------------------------- | -------- |
| GET  | `/permission`                   | 权限申请页    |
| POST | `/api/permission-apply`         | 申请权限     |
| GET  | `/api/user-permissions`         | 获取用户权限列表 |
| POST | `/api/delete-permission`        | 删除用户权限   |
| POST | `/api/batch-approve-permission` | 批量审批权限   |

***

## 💾 数据库设计

系统使用 MySQL 数据库，启动时自动检测并创建缺失的表。包含以下核心表：

### 用户相关表

| 表名                            | 说明                             |
| ----------------------------- | ------------------------------ |
| `user_info`                   | 用户信息（ID、用户名、密码哈希、邮箱、手机号、头像）    |
| `login_log`                   | 登录日志（用户ID、IP、时间、浏览器、地理位置、风险标记） |
| `user_permission`             | 用户权限（用户ID、权限类型）                |
| `user_permission_application` | 权限申请记录（用户ID、权限类型、申请时间）         |

### 开发者相关表

| 表名                         | 说明                                                    |
| -------------------------- | ----------------------------------------------------- |
| `developer_apps`           | 开发者应用（应用ID、开发者ID、名称、App Secret哈希、状态）                  |
| `developer_authorizations` | 用户授权码（应用ID、用户ID、授权码、有效期、状态、权限限制）                      |
| `app_configurations`       | 应用配置（回调地址、更新时间）                                       |
| `authorization_log`        | 授权操作日志（user\_id、app\_id、action、detail、ip、created\_at） |

### 表结构详情

```sql
-- 用户信息表
CREATE TABLE user_info (
    id VARCHAR(15) PRIMARY KEY,
    Name VARCHAR(50) NOT NULL,
    Password VARCHAR(255) NOT NULL,
    mail VARCHAR(100),
    phone VARCHAR(15),
    avatar VARCHAR(255) DEFAULT '/static/img/default_avatar.png',
    created_at DATETIME,
    last_login DATETIME,
    last_ip VARCHAR(45)
);

-- 登录日志表
CREATE TABLE login_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(15) NOT NULL,
    ip VARCHAR(45),
    time DATETIME(3),
    is_danger TINYINT DEFAULT 0,
    browser VARCHAR(200),
    is_cookie TINYINT DEFAULT 0,
    place VARCHAR(100)
);

-- 用户权限表
CREATE TABLE user_permission (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(15) NOT NULL,
    type VARCHAR(50) NOT NULL
);

-- 权限申请表
CREATE TABLE user_permission_application (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(15) NOT NULL,
    type VARCHAR(50) NOT NULL,
    time DATETIME
);

-- 开发者应用表
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
);

-- 授权码表
CREATE TABLE developer_authorizations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    app_id VARCHAR(15) NOT NULL,
    user_id VARCHAR(15) NOT NULL,
    auth_code VARCHAR(30) NOT NULL,
    created_at DATETIME,
    expires_at DATETIME,
    status ENUM('active', 'cancelled', 'blacklisted') DEFAULT 'active',
    permission_restrictions JSON
);

-- 应用配置表
CREATE TABLE app_configurations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    app_id VARCHAR(15) NOT NULL UNIQUE,
    login_callback_url VARCHAR(255),
    verification_callback_url VARCHAR(255),
    scope VARCHAR(255),
    updated_at DATETIME
);

-- 授权操作日志表
CREATE TABLE authorization_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(15) NOT NULL,
    app_id VARCHAR(15),
    action VARCHAR(50) NOT NULL,
    detail TEXT,
    ip VARCHAR(45),
    created_at DATETIME
);
```

***

## 🔐 权限体系

系统采用简化的三级权限管理：

```
管理员 (Administrator)
  ├── 用户管理（查看、编辑、删除用户）
  ├── 权限管理（审批/拒绝权限申请）
  ├── 登录日志（查看所有用户登录记录）
  ├── 应用审核（审核开发者应用申请）
  └── 应用管理（管理所有应用）

开发者 (Developer)
  ├── 应用创建（创建第三方应用）
  ├── 应用管理（查看、配置、删除自己的应用）
  ├── OAuth API（调用用户信息API、验证码API）
  └── 回调配置（设置登录/验证码回调地址）

普通用户 (User)
  ├── 个人信息管理（查看、编辑自己的信息）
  ├── 头像管理（上传、修改头像）
  ├── 密码修改（修改登录密码）
  ├── 权限申请（申请开发者权限）
  └── OAuth授权（授权第三方应用访问）
```

***

## 📬 联系方式

| 方式     | 信息                                             |
| ------ | ---------------------------------------------- |
| 🌐 网站  | [snyqt-account.iepose.cn](https://snyqt-account.iepose.cn) |
| 📧 邮箱  | <snyqt@qq.com>                                 |
| 💬 QQ群 | 1106802055（SNYQT-ACCOUNT交流群）                   |

***

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

### 开发流程

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

### 代码规范

- 使用 4 空格缩进
- 遵循 PEP 8 Python 代码规范
- 提交前运行测试

***

## 📄 开源协议

本项目基于 [MIT License](LICENSE) 开源。

**MIT License**

Copyright © 2026 少年友晴天

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

***

<div align="center">
  <p>Made with by <a href="https://github.com/snyqt">SNYQT</a></p>
  <p>&copy; 2026 少年友晴天 | 以科技化的方式，无限进步！</p>
</div>
