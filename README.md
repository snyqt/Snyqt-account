<div align="center">
  <img src="static/img/logo.png" alt="SNYQT Logo" width="120" height="120" style="border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">

# 少年友晴天 - 统一账户认证系统

  <p>
    <strong>SNYQT 统一账户认证与 OAuth 授权平台</strong>
  </p>

  <p>
    <a href="https://github.com/snyqt/snyqt-account"><img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python"></a>
    <a href="https://github.com/snyqt/snyqt-account"><img src="https://img.shields.io/badge/Flask-2.3.3-green.svg" alt="Flask"></a>
    <a href="https://github.com/snyqt/snyqt-account"><img src="https://img.shields.io/badge/MySQL-5.7+-orange.svg" alt="MySQL"></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License"></a>
  </p>

  <p>
    <a href="https://account.snyqt.top">在线演示</a> •
    <a href="#本地开发">本地开发</a> •
    <a href="#docker-部署">Docker 部署</a> •
    <a href="#联系方式">联系方式</a>
  </p>
</div>

---

## 目录

- [项目简介](#项目简介)
- [功能特性](#功能特性)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [环境变量清单](#环境变量清单)
- [本地开发](#本地开发)
- [Docker 部署](#docker-部署)
- [Gitea Actions 自动部署（内部使用）](#gitea-actions-自动部署内部使用)
- [API 概览](#api-概览)
- [数据库设计](#数据库设计)
- [权限体系](#权限体系)
- [故障排查](#故障排查)
- [联系方式](#联系方式)
- [贡献指南](#贡献指南)
- [开源协议](#开源协议)

---

## 项目简介

少年友晴天（SNYQT）统一账户认证系统，为 SNYQT 生态内各站点提供统一的账户注册、登录与身份认证入口。

- **统一账户**：一套账号覆盖全部站点，集中管理用户资料、密码、头像与安全设置。
- **OAuth 2.0 授权**：第三方应用通过标准授权流程获取用户信息与验证码能力，支持回调地址与 Scope 权限范围配置。
- **多站点单点登录**：登录态统一由本系统签发，各子站共享身份，避免重复注册与多处维护。
- **安全能力**：邮箱 / 短信验证码、Cloudflare Turnstile 人机验证、登录风控、MFA（TOTP / WebAuthn）与登录日志审计。

系统全部配置由环境变量注入，仓库内不含任何密钥；**缺少必填环境变量时应用会拒绝启动（fail fast）**。

---

## 功能特性

### 用户认证与安全

- 用户注册 / 登录 / 忘记密码
- 邮箱验证码与短信验证码（阿里云短信服务）
- Cloudflare Turnstile 人机验证，支持全局验证中间件
- 登录风控检测（异地登录、新设备检测、失败次数阈值）
- 多因子认证（MFA）：TOTP 动态口令与 WebAuthn/FIDO2 安全密钥
- 风险登录二次验证（邮箱 + 手机双重验证）
- 记住我（7 天免登录）、会话自动过期（10 分钟）
- SHA-256 密码哈希存储

### 用户管理

- 个人信息查看与编辑（用户名、邮箱、手机号、头像）
- 密码修改（旧密码验证 + 新密码强度检查）
- 头像上传与裁剪（Pillow 图片处理）
- 管理员查看 / 修改所有用户信息

### 用户界面

- 深色 / 浅色主题切换，自动记住用户偏好
- 基于 Logo 色彩的品牌化渐变配色
- 响应式布局，适配移动设备
- 首页功能卡片导航与过渡动画

### 权限管理

- 三类角色：管理员、开发者、普通用户
- 权限申请与审批（支持批量审批）
- 管理员拥有全部管理权限

### 开发者平台（OAuth 2.0）

- OAuth 2.0 授权流程与应用审核（生成 App ID / App Secret）
- Account API（获取用户名、头像、用户 ID）
- 验证码 API（邮箱 / 手机验证码发送与验证）
- 登录回调与验证码回调机制
- Scope 权限范围配置（`userinfo` / `email_code` / `phone_code`）
- 标准 OIDC 发现文档与用户信息端点

### 登录日志

- 用户个人登录记录查询
- 管理员全局登录日志查询（按用户 / 时间 / IP 筛选）
- 浏览器、设备与 IP 地理位置记录

### 第三方安全管理

- 已授权应用列表（授权时间、权限范围）
- 取消授权与拉黑（黑名单）机制
- 细粒度权限限制（禁止发送邮件 / 短信验证码 / 访问个人信息）
- 授权操作日志（操作人、类型、详情、IP、时间）

---

## 技术栈

| 类别 | 技术 |
| --- | --- |
| 后端框架 | Flask 2.3.3 |
| 数据库 | MySQL 5.7+（PyMySQL 1.1.0） |
| 图片处理 | Pillow 12.1.1 |
| 短信服务 | 阿里云短信（alibabacloud_dypnsapi20170525） |
| 人机验证 | Cloudflare Turnstile |
| 多因子认证 | pyotp 2.9.0 / qrcode 7.4.2 / webauthn 2.3.0 |
| 前端 | HTML5 / CSS3 / 原生 JavaScript |
| 图标 | Font Awesome 6 |
| 部署 | Docker + uWSGI / 直接运行 |
| 授权协议 | OAuth 2.0 / OIDC |
| 运行环境 | Python 3.11+ |

---

## 项目结构

```
Snyqt-account/
├── run.py                          # 应用入口（WSGI callable: app）
├── config.py                       # 配置模块：只从环境变量读取，无明文密钥
├── requirements.txt                # Python 依赖列表
├── Dockerfile                      # Docker 镜像定义（uWSGI 启动）
├── uwsgi.ini                       # uWSGI 配置文件
├── LICENSE                         # MIT 开源协议
├── README.md                       # 项目说明文档
├── .gitignore                      # Git 忽略规则（含 .env）
├── .env                            # 本地环境变量文件（不入库）
├── .gitea/
│   └── workflows/
│       └── deploy.yml              # Gitea Actions 自动构建与部署工作流
│
├── app/                            # 应用主目录
│   ├── __init__.py                 # 应用工厂（Flask 实例创建、蓝图注册）
│   ├── env.py                      # 运行环境探测（本地 / Docker / uWSGI / 生产）
│   ├── env_config.py               # 运行参数与 Turnstile、风控、MFA 配置装配
│   │
│   ├── models/                     # 数据模型
│   │   ├── __init__.py
│   │   └── db.py                   # 数据库连接、建表与校验
│   │
│   ├── auth/                       # 认证模块
│   │   ├── routes.py               # 登录 / 注册 / 验证码 / 忘记密码 / 2FA
│   │   └── utils.py                # 密码哈希、邮件、短信、风控工具
│   │
│   ├── mfa/                        # 多因子认证模块
│   │   └── routes.py               # TOTP / WebAuthn 绑定与校验
│   │
│   ├── user/                       # 用户模块
│   │   ├── routes.py               # 个人信息 / 头像 / 密码
│   │   └── utils.py                # 用户工具函数
│   │
│   ├── admin/                      # 管理员模块
│   │   ├── routes.py               # 用户 / 权限 / 日志 / 应用管理
│   │   └── utils.py                # 管理员工具函数
│   │
│   ├── permission/                 # 权限模块
│   │   ├── routes.py               # 权限申请 / 审批 / 删除
│   │   ├── utils.py                # 权限检查工具
│   │   └── decorators.py           # 权限装饰器
│   │
│   ├── developer/                  # 开发者模块
│   │   └── routes.py               # 应用管理、OAuth / OIDC 端点
│   │
│   ├── security/                   # 第三方安全管理模块
│   │   └── routes.py               # 授权列表、取消授权、黑名单、权限限制
│   │
│   ├── turnstile/                  # Turnstile 人机验证模块
│   │   └── routes.py               # 验证页与校验逻辑
│   │
│   ├── middleware/                 # 全局中间件
│   │   └── turnstile_middleware.py # Turnstile 全局验证中间件
│   │
│   └── templates/                  # Jinja2 模板
│       ├── index.html              # 首页
│       ├── login.html              # 登录 / 注册页
│       ├── forgot_password.html    # 忘记密码页
│       ├── profile.html            # 个人信息页
│       ├── mfa_settings.html       # MFA 设置页
│       ├── permission.html         # 权限申请页
│       ├── app_management.html     # 管理员应用管理
│       ├── app_review.html         # 应用审核页
│       ├── developer_app_management.html  # 开发者应用管理
│       ├── developer_docs.html     # 开发者文档
│       ├── oauth_authorize.html    # OAuth 授权确认页
│       ├── third_party_security.html     # 第三方安全管理
│       ├── user_info_management.html     # 用户信息管理（管理员）
│       ├── user_permission_management.html # 权限管理（管理员）
│       ├── user_login_log.html     # 用户登录日志
│       ├── admin_login_log.html    # 管理员登录日志
│       ├── authorization_log.html  # 授权操作日志
│       ├── turnstile_verify.html   # Turnstile 验证页
│       └── 401 / 403 / 404 / 500.html    # 错误页
│
└── static/                         # 静态资源
    ├── img/                        # 图片资源（logo、默认头像、预设头像、用户头像）
    ├── css/                        # 样式（common.css、theme-toggle.css、Font Awesome）
    ├── js/                         # 前端脚本（theme-toggle.js 等）
    └── temp/                       # 临时文件（容器内挂载持久化）
```

---

## 环境变量清单

应用只从进程环境变量读取配置，**仓库内不存在任何明文密钥**。下表与 `config.py` 逐项对应。

| 变量名 | 是否必填 | 是否敏感 | 说明 | 默认值 |
| --- | --- | --- | --- | --- |
| `SECRET_KEY` | 是 | 是 | Flask 会话签名密钥（建议 32 位以上随机字符串）。必须由部署者在 Gitea Actions Secrets（或本地 `.env`）中配置，否则应用拒绝启动 | —（必填，无默认） |
| `DB_USER` | 是 | 否 | 数据库用户名。必须由部署者在 Gitea Actions Secrets（或本地 `.env`）中配置，否则应用拒绝启动 | —（必填，无默认） |
| `DB_PASSWORD` | 是 | 是 | 数据库密码。必须由部署者在 Gitea Actions Secrets（或本地 `.env`）中配置，否则应用拒绝启动 | —（必填，无默认） |
| `SMTP_SENDER` | 是 | 否 | 发件人邮箱地址。必须由部署者在 Gitea Actions Secrets（或本地 `.env`）中配置，否则应用拒绝启动 | —（必填，无默认） |
| `SMTP_PASSWORD` | 是 | 是 | SMTP 授权码 / 登录密码。必须由部署者在 Gitea Actions Secrets（或本地 `.env`）中配置，否则应用拒绝启动 | —（必填，无默认） |
| `ALIYUN_ACCESS_KEY_ID` | 是 | 是 | 阿里云短信 AccessKey ID。必须由部署者在 Gitea Actions Secrets（或本地 `.env`）中配置，否则应用拒绝启动 | —（必填，无默认） |
| `ALIYUN_ACCESS_KEY_SECRET` | 是 | 是 | 阿里云短信 AccessKey Secret。必须由部署者在 Gitea Actions Secrets（或本地 `.env`）中配置，否则应用拒绝启动 | —（必填，无默认） |
| `TURNSTILE_SECRET_KEY` | 是 | 是 | Cloudflare Turnstile 服务端密钥。必须由部署者在 Gitea Actions Secrets（或本地 `.env`）中配置，否则应用拒绝启动 | —（必填，无默认） |
| `DB_HOST` | 否 | 否 | 数据库主机地址 | `localhost` |
| `DB_PORT` | 否 | 否 | 数据库端口（必须为整数） | `3306` |
| `DB_NAME` | 否 | 否 | 数据库名称 | `Snyqt-account` |
| `SMTP_SERVER` | 否 | 否 | SMTP 服务器地址 | `smtp.exmail.qq.com` |
| `SMTP_PORT` | 否 | 否 | SMTP 端口（必须为整数） | `465` |
| `ALIYUN_SIGN_NAME` | 否 | 否 | 阿里云短信签名 | `速通互联验证码` |
| `ALIYUN_TEMPLATE_CODE` | 否 | 否 | 阿里云短信模板 CODE | `100001` |
| `TURNSTILE_ENABLED` | 否 | 否 | 是否启用全局 Turnstile 验证，取值为 `true` / `false` | `true` |
| `TURNSTILE_SITEKEY` | 否 | 否 | Turnstile 站点密钥（前端可见） | `0x4AAAAAACyxdKEqrmJV4bJn` |
| `TURNSTILE_VERIFY_URL` | 否 | 否 | Turnstile 服务端校验接口 | `https://challenges.cloudflare.com/turnstile/v0/siteverify` |
| `APP_PORT` | 否 | 否 | 应用监听端口（必须为整数） | `5000` |
| `TIMEZONE` | 否 | 否 | 应用时区 | `Asia/Shanghai` |
| `FORCE_MFA` | 否 | 否 | 是否强制启用多因子认证，取值为 `true` / `false` | `true` |
| `VERIFICATION_CODE_EXPIRE` | 否 | 否 | 验证码有效期（秒，必须为整数） | `300` |
| `WEBAUTHN_RP_ID` | 否 | 否 | WebAuthn/FIDO2 的 RP ID（生产环境域名） | `account.snyqt.top` |
| `WEBAUTHN_ORIGIN` | 否 | 否 | WebAuthn 允许的源（完整协议 + 域名） | `https://account.snyqt.top` |
| `ENVIRONMENT_MODE` | 否 | 否 | 运行环境模式，取值 `auto` / `development` / `production` | `auto` |
| `OIDC_ISSUER` | 否 | 否 | OIDC 签发者标识；未配置时按请求头推导（部署工作流默认注入 `https://account.snyqt.top`） | `https://account.snyqt.top`（工作流默认） |

> 空字符串等同未配置：必填项为空会触发启动校验失败，可选变量为空则回退上表默认值，因此 `-e KEY=` 这类空值不会覆盖已有默认配置。整数型变量（`DB_PORT`、`SMTP_PORT`、`APP_PORT`、`VERIFICATION_CODE_EXPIRE`）若无法解析为整数会直接报错。

---

## 本地开发

### 1. 克隆仓库

```bash
git clone https://github.com/snyqt/snyqt-account.git
cd snyqt-account
```

### 2. 创建虚拟环境并安装依赖

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt
```

### 3. 配置环境变量

仓库中**没有**任何配置文件模板，也不需要提交任何密钥。本地请在项目根目录自行创建 `.env` 文件：该文件已被 `.gitignore` 忽略（规则为 `.env`、`.env.*`），**不会进入版本库**，仅用于本机保存变量值。

`.env` 内容示例（键名即环境变量名，敏感值一律用 `your-` 前缀占位）：

```dotenv
# ===== 必填（8 项，缺失则无法启动）=====
SECRET_KEY=your-random-secret-key
DB_USER=your-db-user
DB_PASSWORD=your-db-password
SMTP_SENDER=your-sender@your-domain.com
SMTP_PASSWORD=your-smtp-auth-code
ALIYUN_ACCESS_KEY_ID=your-access-key-id
ALIYUN_ACCESS_KEY_SECRET=your-access-key-secret
TURNSTILE_SECRET_KEY=your-turnstile-secret-key

# ===== 可选（留空回退代码默认值）=====
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=Snyqt-account
SMTP_SERVER=smtp.exmail.qq.com
SMTP_PORT=465
ALIYUN_SIGN_NAME=your-sms-sign-name
ALIYUN_TEMPLATE_CODE=your-template-code
TURNSTILE_ENABLED=true
TURNSTILE_SITEKEY=your-turnstile-site-key
FORCE_MFA=true
VERIFICATION_CODE_EXPIRE=300
WEBAUTHN_RP_ID=localhost
WEBAUTHN_ORIGIN=http://localhost:5000
```

应用读取的是**进程环境变量**，`.env` 不会自动加载，需要先把它导入当前 shell：

```bash
# Linux / macOS / Git Bash
set -a; source .env; set +a
```

```powershell
# Windows PowerShell（逐条设置，示例）
$env:SECRET_KEY = "your-random-secret-key"
$env:DB_USER = "your-db-user"
$env:DB_PASSWORD = "your-db-password"
$env:SMTP_SENDER = "your-sender@your-domain.com"
$env:SMTP_PASSWORD = "your-smtp-auth-code"
$env:ALIYUN_ACCESS_KEY_ID = "your-access-key-id"
$env:ALIYUN_ACCESS_KEY_SECRET = "your-access-key-secret"
$env:TURNSTILE_SECRET_KEY = "your-turnstile-secret-key"
```

也可以完全不用 `.env`，直接按上面的 `export VAR=value`（PowerShell 为 `$env:VAR = "value"`）方式在终端设置。

> **预期行为**：只要缺少任一必填环境变量（或值为空字符串），`python run.py` 会在导入配置阶段立即抛出 `RuntimeError` 并退出，错误信息会逐条列出缺失的变量名与用途。这不是 bug，而是防止带病启动的保护机制。

### 4. 初始化数据库

```sql
CREATE DATABASE `Snyqt-account` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

> 应用启动时会自动检测并创建缺失的表结构，无需手动导入 SQL 文件。

### 5. 启动应用

```bash
python run.py
```

应用默认监听 `http://localhost:5000`（可通过 `APP_PORT` 修改），按 `Ctrl+C` 停止。

---

## Docker 部署

### 1. 构建镜像

```bash
docker build -t snyqt-account .
```

### 2. 运行容器

敏感项一律在运行时通过 `-e` 注入，镜像内**不含任何密钥**。示例中的尖括号为占位说明，请替换为真实值：

```bash
docker run -d \
  --name snyqt-account \
  --restart unless-stopped \
  -p 5000:5000 \
  -e SECRET_KEY='<在此填入你的 Flask 会话密钥>' \
  -e DB_HOST='192.168.10.10' \
  -e DB_PORT='3306' \
  -e DB_USER='<在此填入你的数据库用户名>' \
  -e DB_PASSWORD='<在此填入你的数据库密码>' \
  -e DB_NAME='Snyqt-account' \
  -e SMTP_SERVER='smtp.exmail.qq.com' \
  -e SMTP_PORT='465' \
  -e SMTP_SENDER='<在此填入你的发件人邮箱>' \
  -e SMTP_PASSWORD='<在此填入你的 SMTP 授权码>' \
  -e ALIYUN_ACCESS_KEY_ID='<在此填入你的阿里云 AccessKey ID>' \
  -e ALIYUN_ACCESS_KEY_SECRET='<在此填入你的阿里云 AccessKey Secret>' \
  -e ALIYUN_SIGN_NAME='速通互联验证码' \
  -e ALIYUN_TEMPLATE_CODE='100001' \
  -e TURNSTILE_ENABLED='true' \
  -e TURNSTILE_SITEKEY='<在此填入你的 Turnstile 站点密钥>' \
  -e TURNSTILE_SECRET_KEY='<在此填入你的 Turnstile 服务端密钥>' \
  -e APP_PORT='5000' \
  -e TIMEZONE='Asia/Shanghai' \
  -e FORCE_MFA='true' \
  -e VERIFICATION_CODE_EXPIRE='300' \
  -e WEBAUTHN_RP_ID='account.snyqt.top' \
  -e WEBAUTHN_ORIGIN='https://account.snyqt.top' \
  -e OIDC_ISSUER='https://account.snyqt.top' \
  -v "$(pwd)/logs:/app/logs" \
  -v "$(pwd)/static/temp:/app/static/temp" \
  -v "$(pwd)/static/img/user_avatar:/app/static/img/user_avatar" \
  snyqt-account
```

其中 `SECRET_KEY`、`DB_PASSWORD`、`SMTP_PASSWORD`、`ALIYUN_ACCESS_KEY_ID`、`ALIYUN_ACCESS_KEY_SECRET`、`TURNSTILE_SECRET_KEY` 为敏感变量，生产环境由 Gitea Secrets 注入；其余为公开默认值。

### 3. 使用 Docker Compose

```yaml
services:
  web:
    build: .
    container_name: snyqt-account
    restart: unless-stopped
    ports:
      - "5000:5000"
    environment:
      # ===== 敏感变量，生产环境由 Gitea Secrets / 本地密钥文件注入 =====
      SECRET_KEY: "<在此填入你的 Flask 会话密钥>"
      DB_PASSWORD: "<在此填入你的数据库密码>"
      SMTP_PASSWORD: "<在此填入你的 SMTP 授权码>"
      ALIYUN_ACCESS_KEY_ID: "<在此填入你的阿里云 AccessKey ID>"
      ALIYUN_ACCESS_KEY_SECRET: "<在此填入你的阿里云 AccessKey Secret>"
      TURNSTILE_SECRET_KEY: "<在此填入你的 Turnstile 服务端密钥>"
      # ===== 非敏感变量，使用默认值 =====
      DB_HOST: "db"
      DB_PORT: "3306"
      DB_USER: "snyqt"
      DB_NAME: "Snyqt-account"
      SMTP_SERVER: "smtp.exmail.qq.com"
      SMTP_PORT: "465"
      SMTP_SENDER: "<在此填入你的发件人邮箱>"
      ALIYUN_SIGN_NAME: "速通互联验证码"
      ALIYUN_TEMPLATE_CODE: "100001"
      TURNSTILE_ENABLED: "true"
      TURNSTILE_SITEKEY: "<在此填入你的 Turnstile 站点密钥>"
      FORCE_MFA: "true"
      VERIFICATION_CODE_EXPIRE: "300"
      WEBAUTHN_RP_ID: "account.snyqt.top"
      WEBAUTHN_ORIGIN: "https://account.snyqt.top"
      OIDC_ISSUER: "https://account.snyqt.top"
    volumes:
      - ./logs:/app/logs
      - ./static/temp:/app/static/temp
      - ./static/img/user_avatar:/app/static/img/user_avatar
    depends_on:
      - db

  db:
    image: mysql:5.7
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: "<在此填入你的 MySQL root 密码>"
      MYSQL_DATABASE: "Snyqt-account"
      MYSQL_USER: "snyqt"
      MYSQL_PASSWORD: "<在此填入你的数据库密码>"
    volumes:
      - mysql_data:/var/lib/mysql

volumes:
  mysql_data:
```

> Compose 中的密码请改用 `.env` 文件 + `docker compose --env-file .env`，或由 CI 注入，不要硬编码提交。

启动服务：

```bash
docker-compose up -d
```

镜像内不含任何密钥，所有敏感配置完全依赖运行时 `-e`（或 Compose `environment`）注入。

---

## Gitea Actions 自动部署（内部使用）

<details>
<summary>点击展开：内部 Gitea 自动部署说明（外部开源使用者无需关注）</summary>

### 触发条件

向 `main` 分支 push 后自动触发（也支持在 Gitea 网页端手动触发 workflow）。

### 部署流程

1. **checkout**：拉取最新代码；
2. **准备目录与网络**：创建数据子目录，确保 Docker 网络 `Snyqt-net` 存在；
3. **docker build**：构建 `snyqt-account:<commit前7位>` 与 `snyqt-account:latest` 镜像；
4. **替换容器**：停止并删除旧容器 `snyqt-account-1`，用新镜像启动同名容器；
5. **健康检查**：轮询容器 `HEALTHCHECK` 状态，并请求首页确认 HTTP 可用；失败则打印 `docker logs` 尾部并以非零状态退出；
6. **清理**：回收 168 小时以上的旧镜像。

### Secret 配置位置

仓库页面 → **Settings** → **Actions** → **Secrets** → **Add secret**。

命名规则：

- 仅允许大写字母、数字与下划线；
- 不能以 `GITEA_` 或 `GITHUB_` 开头；
- 保存后不可再查看明文，只能覆盖修改。

### Secrets 与 Variables 的区别

| 类型 | 引用方式 | 特性 |
| --- | --- | --- |
| Secrets | `${{ secrets.XXX }}` | 加密存储，日志自动掩码为 `***`，适合密钥、密码、AccessKey |
| Variables | `${{ vars.XXX }}` | 明文存储，可能原样打印在日志中，适合主机、端口、开关等公开配置 |

分工原则：**会泄密的放 Secrets，不怕看的放 Variables**。

### 本项目需要配置的 Secrets

| Secret 名称 | 用途 |
| --- | --- |
| `SECRET_KEY` | Flask 会话签名密钥 |
| `DB_PASSWORD` | 数据库密码 |
| `SMTP_PASSWORD` | SMTP 授权码 / 登录密码 |
| `ALIYUN_ACCESS_KEY_ID` | 阿里云短信 AccessKey ID |
| `ALIYUN_ACCESS_KEY_SECRET` | 阿里云短信 AccessKey Secret |
| `TURNSTILE_SECRET_KEY` | Cloudflare Turnstile 服务端密钥 |

### 可选 Variables

| 变量名 | 工作流内默认值 |
| --- | --- |
| `DB_HOST` | `192.168.10.10` |
| `DB_PORT` | `3306` |
| `DB_USER` | `snyqt-study` |
| `DB_NAME` | `Snyqt-account` |
| `SMTP_SERVER` | `smtp.exmail.qq.com` |
| `SMTP_PORT` | `465` |
| `SMTP_SENDER` | `snyqt-noreply@snyqt.top` |
| `ALIYUN_SIGN_NAME` | `速通互联验证码` |
| `ALIYUN_TEMPLATE_CODE` | `100001` |
| `TURNSTILE_ENABLED` | `true` |
| `TURNSTILE_SITEKEY` | `0x4AAAAAACyxdKEqrmJV4bJn` |
| `FORCE_MFA` | `true` |
| `VERIFICATION_CODE_EXPIRE` | `300` |
| `WEBAUTHN_RP_ID` | `account.snyqt.top` |
| `WEBAUTHN_ORIGIN` | `https://account.snyqt.top` |
| `OIDC_ISSUER` | `https://account.snyqt.top` |

上述 Variables 未配置时，工作流自动使用表中默认值，不影响部署。

### 部署产物

| 项目 | 值 |
| --- | --- |
| 访问地址 | `http://192.168.10.10:39731` |
| 容器名 | `snyqt-account-1` |
| 宿主机端口 → 容器端口 | `39731` → `5000` |
| 数据目录 | `/volume1/docker/snyqt-account` |
| 日志挂载 | `/volume1/docker/snyqt-account/app_logs` → `/app/logs` |
| 临时文件挂载 | `/volume1/docker/snyqt-account/app_static_temp` → `/app/static/temp` |
| 头像挂载 | `/volume1/docker/snyqt-account/app_static_img_user_avatar` → `/app/static/img/user_avatar` |
| Docker 网络 | `Snyqt-net` |

### 重要说明

- Secrets 必须由部署者**在 Gitea 网页后台手动添加**，这是仓库外操作，代码与工作流都无法自动完成；缺少任何一个 Secret，容器会因启动校验失败而反复重启。
- 本仓库在 Gitea 与 GitHub 上内容完全一致（同一 `main` 分支），外部开源使用者无需关注此章节，按「本地开发」或「Docker 部署」自行部署即可。

</details>

---

## API 概览

### 认证相关 API

| 方法 | 端点 | 说明 |
| --- | --- | --- |
| POST | `/login` | 用户登录 |
| POST | `/register` | 用户注册 |
| POST | `/logout` | 用户登出 |
| POST | `/send_code` | 发送邮箱验证码 |
| POST | `/verify_code` | 校验邮箱验证码 |
| GET / POST | `/forgot_password` | 忘记密码页面 / 提交重置 |
| POST | `/api/send-sms-code` | 发送短信验证码 |
| POST | `/api/verify-sms-code` | 校验短信验证码 |

### OAuth 2.0 授权 API

| 方法 | 端点 | 说明 |
| --- | --- | --- |
| GET | `/oauth/authorize` | OAuth 授权入口（`app_id`、`redirect_uri`） |
| POST | `/oauth/authorize/confirm` | 确认授权并签发授权码 |
| POST | `/api/oauth/userinfo` | 用授权码换取用户信息 |
| POST | `/api/oauth/send-verification` | 第三方应用发送验证码 |

授权流程：

```
1. 用户访问第三方应用
2. 应用重定向到授权页：GET /oauth/authorize?app_id=xxx&redirect_uri=xxx
3. 用户确认授权：POST /oauth/authorize/confirm { app_id, redirect_uri }
4. 回调携带授权码 auth_code（有效期 1 天）
5. 应用换取用户信息：
   POST /api/oauth/userinfo
   { app_id, app_secret, auth_code }
```

Scope 权限范围：

| scope 值 | 说明 |
| --- | --- |
| `userinfo` | 获取用户基本信息（用户 ID、用户名、头像），默认必选 |
| `email_code` | 允许向用户邮箱发送验证码 |
| `phone_code` | 允许向用户手机发送验证码 |

### 用户管理 API

| 方法 | 端点 | 说明 |
| --- | --- | --- |
| GET | `/profile` | 个人信息页 |
| POST | `/api/update-profile` | 更新个人信息 |
| POST | `/api/update-avatar` | 更新头像 |
| POST | `/api/change-password` | 修改密码 |
| GET | `/api/user-info` | 获取用户信息 |
| GET | `/api/get-user-permissions` | 获取用户权限 |

### 开发者 API

| 方法 | 端点 | 说明 |
| --- | --- | --- |
| GET | `/developer-docs` | 开发者文档页 |
| GET | `/developer-app-management` | 开发者应用管理页 |
| POST | `/api/developer/create-app` | 创建应用 |
| GET | `/api/developer/apps` | 获取应用列表 |
| DELETE | `/api/developer/delete-app` | 删除应用 |
| POST | `/api/developer/configure-callback` | 配置回调地址与 Scope |
| GET | `/api/developer/app-secret/<app_id>` | 获取 App Secret |
| GET | `/api/developer/app-config/<app_id>` | 获取应用配置 |

### 管理员 API

| 方法 | 端点 | 说明 |
| --- | --- | --- |
| GET | `/admin/users` | 用户信息管理页 |
| GET | `/admin/login-log` | 管理员登录日志页 |
| GET | `/admin/user-login-log` | 用户登录日志页 |
| GET | `/admin/app-review` | 应用审核页 |
| GET | `/admin/app-management` | 应用管理页 |
| GET | `/api/admin/users` | 获取用户列表 |
| POST | `/api/admin/update-user` | 更新用户信息 |
| POST | `/api/admin/delete-user` | 删除用户 |
| GET | `/api/admin/pending-apps` | 获取待审核应用 |
| POST | `/api/admin/approve-app` | 审批通过应用 |
| POST | `/api/admin/reject-app` | 拒绝应用 |
| GET | `/api/admin/all-apps` | 获取所有应用 |
| POST | `/api/admin/update-app` | 更新应用信息 |
| DELETE | `/api/admin/delete-app` | 删除应用 |

### 权限管理 API

| 方法 | 端点 | 说明 |
| --- | --- | --- |
| GET | `/permission` | 权限申请页 |
| POST | `/api/permission-apply` | 申请权限 |
| GET | `/api/user-permissions` | 获取用户权限列表 |
| POST | `/api/delete-permission` | 删除用户权限 |
| POST | `/api/batch-approve-permission` | 批量审批权限 |

### 第三方安全管理 API

| 方法 | 端点 | 说明 |
| --- | --- | --- |
| GET | `/api/third-party-security` | 获取已授权应用列表（`status` 可选 `active` / `blacklisted`） |
| POST | `/api/third-party/cancel-auth` | 取消授权（不拉黑） |
| POST | `/api/third-party/blacklist-app` | 拉黑应用 |
| POST | `/api/third-party/restore-auth` | 解除黑名单 |
| POST | `/api/third-party/restrict-permission` | 设置权限限制（`no_email` 等） |
| GET | `/api/authorization-log` | 获取授权操作日志（`search` 可选） |

请求体统一为 `application/json`，例如：

```json
{ "app_id": "xxx", "auth_id": 1 }
```

---

## 数据库设计

系统使用 MySQL，启动时自动检测并创建缺失的表。

| 表名 | 说明 |
| --- | --- |
| `user_info` | 用户信息（ID、用户名、密码哈希、邮箱、手机号、头像、创建与登录时间） |
| `login_log` | 登录日志（用户 ID、IP、时间、浏览器、地理位置、风险标记） |
| `user_permission` | 用户权限（用户 ID、权限类型） |
| `user_permission_application` | 权限申请记录（用户 ID、权限类型、申请时间） |
| `developer_apps` | 开发者应用（应用 ID、开发者 ID、名称、App Secret 哈希、状态） |
| `developer_authorizations` | 用户授权码（应用 ID、用户 ID、授权码、有效期、状态、权限限制） |
| `app_configurations` | 应用配置（回调地址、Scope、更新时间） |
| `authorization_log` | 授权操作日志（用户 ID、应用 ID、操作、详情、IP、时间） |

核心表结构：

```sql
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

CREATE TABLE user_permission (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(15) NOT NULL,
    type VARCHAR(50) NOT NULL
);

CREATE TABLE user_permission_application (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(15) NOT NULL,
    type VARCHAR(50) NOT NULL,
    time DATETIME
);

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

CREATE TABLE app_configurations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    app_id VARCHAR(15) NOT NULL UNIQUE,
    login_callback_url VARCHAR(255),
    verification_callback_url VARCHAR(255),
    scope VARCHAR(255),
    updated_at DATETIME
);

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

---

## 权限体系

```
管理员 (Administrator)
  ├── 用户管理（查看、编辑、删除用户）
  ├── 权限管理（审批 / 拒绝权限申请）
  ├── 登录日志（查看所有用户登录记录）
  ├── 应用审核（审核开发者应用申请）
  └── 应用管理（管理所有应用）

开发者 (Developer)
  ├── 应用创建（创建第三方应用）
  ├── 应用管理（查看、配置、删除自己的应用）
  ├── OAuth API（用户信息 API、验证码 API）
  └── 回调配置（设置登录 / 验证码回调地址）

普通用户 (User)
  ├── 个人信息管理（查看、编辑自己的信息）
  ├── 头像管理（上传、修改头像）
  ├── 密码修改（修改登录密码）
  ├── 权限申请（申请开发者权限）
  └── OAuth 授权（授权第三方应用访问）
```

---

## 故障排查

| 现象 | 常见原因 | 处理方式 |
| --- | --- | --- |
| 启动即报「缺少必需的环境变量，应用拒绝启动」 | 必填环境变量未设置、为空字符串，或容器 `-e` 未注入 | 按报错列出的变量名补齐 `SECRET_KEY`、`DB_USER`、`DB_PASSWORD`、`SMTP_SENDER`、`SMTP_PASSWORD`、`ALIYUN_ACCESS_KEY_ID`、`ALIYUN_ACCESS_KEY_SECRET`、`TURNSTILE_SECRET_KEY`；确认 shell 已导入 `.env`，容器场景确认 Gitea Secrets 已配置 |
| 数据库连接失败（`Connection refused` / 认证失败） | `DB_HOST` 不可达、`DB_PORT` 错误、库未创建、账号权限不足，或容器内误用 `localhost` | 本地部署时 `DB_HOST` 用 `127.0.0.1`；容器内连接宿主机用宿主机内网 IP 或 `host.docker.internal`，不可写 `localhost`；先执行建库 SQL 并核对账号密码与授权 |
| SMTP 465 端口连接超时或授权码错误 | 465 为 SSL 端口被防火墙拦截、填入的是邮箱登录密码而非授权码 | 改用 `smtp.exmail.qq.com` 等正确服务器并填「授权码」；确认服务器放行 465 出站；必要时改用 587（需服务端支持）并核对 `SMTP_PORT` |
| Turnstile 验证失败 | `TURNSTILE_SITEKEY` 与 `TURNSTILE_SECRET_KEY` 不匹配（站点密钥与服务端密钥来自不同 widget），或域名未在 Turnstile 后台登记 | 在 Cloudflare Turnstile 控制台确认同一站点下成对的 Site Key / Secret Key 并同时更新；核对部署域名；本地调试可临时设 `TURNSTILE_ENABLED=false` |
| 容器反复重启 | 必填环境变量缺失导致启动校验失败、数据库不可达、端口被占用 | `docker logs --tail 200 snyqt-account`（或 `snyqt-account-1`）查看报错首行；确认 8 个必填变量已注入且数据库可连接；检查宿主机端口占用 |
| 健康检查失败（容器 `unhealthy`） | 应用尚未就绪、uWSGI 未监听 5000、`APP_PORT` 与实际监听端口不一致 | `docker inspect --format '{{.State.Health.Status}}' <容器名>`；查看 `/app/logs` 日志；确认 `APP_PORT=5000` 且端口映射正确；等待 start-period 后重试 |

---

## 联系方式

| 方式 | 信息 |
| --- | --- |
| 网站 | [account.snyqt.top](https://account.snyqt.top) |
| 邮箱 | <snyqt@qq.com> |
| QQ 群 | 1106802055（SNYQT-ACCOUNT 交流群） |

---

## 贡献指南

欢迎提交 Issue 和 Pull Request。

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/AmazingFeature`
3. 提交更改：`git commit -m 'Add some AmazingFeature'`
4. 推送分支：`git push origin feature/AmazingFeature`
5. 创建 Pull Request

代码规范：使用 4 空格缩进，遵循 PEP 8；提交前确认应用可正常启动，且**不要提交任何 `.env`、密钥或真实凭据**。

---

## 开源协议

本项目采用 MIT 协议，详见 [LICENSE](LICENSE)。

---

<div align="center">
  <p>Made with by <a href="https://github.com/snyqt">SNYQT</a></p>
  <p>&copy; 2026 少年友晴天 | 以科技化的方式，无限进步！</p>
</div>
