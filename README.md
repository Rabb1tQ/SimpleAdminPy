# SimpleAdminPy 后端

基于 FastAPI + PostgreSQL + Redis 的后台管理系统后端。

## 开源协议

本项目采用 [MIT](./LICENSE) 协议开源，可免费用于商业项目。

**使用要求：** 请在您项目的任意显眼位置（如页面底部、关于页面、README 等）选其一标注来源，帮忙推广一下：

> Powered by [SimpleAdmin](https://github.com/Rabb1tQ/SimpleAdminPy)

感谢支持！欢迎 Star ⭐

## 技术栈

- **FastAPI** - 现代、快速的 Web 框架
- **PostgreSQL** - 关系型数据库
- **SQLAlchemy** - ORM 框架
- **Redis** - 缓存数据库
- **Alembic** - 数据库迁移工具
- **JWT** - 身份认证

## 项目结构

```
SimpleAdminPy/
├── alembic/              # 数据库迁移
│   ├── env.py
│   └── script.py.mako
├── app/
│   ├── api/              # API 路由
│   │   ├── deps.py       # 依赖注入
│   │   ├── registry.py   # 路由自动注册
│   │   ├── auth.py       # 认证接口
│   │   └── system/       # 系统管理模块
│   │       ├── user.py   # 用户接口
│   │       ├── role.py   # 角色接口
│   │       ├── menu.py   # 菜单接口
│   │       └── log.py    # 日志接口
│   ├── core/             # 核心配置
│   │   ├── config.py     # 配置管理
│   │   ├── database.py   # 数据库连接
│   │   ├── redis.py      # Redis 连接
│   │   ├── security.py   # 安全工具
│   │   └── logging.py    # 日志配置
│   ├── models/           # 数据库模型
│   ├── schemas/          # Pydantic 模型
│   └── utils/            # 工具函数
├── main.py               # 应用入口
├── requirements.txt      # 依赖列表
└── alembic.ini           # Alembic 配置
```

## 快速开始

### 1. 安装依赖

#### 方式一：使用 venv（推荐）

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

#### 方式二：使用 Conda

```bash
# 创建虚拟环境（可指定 Python 版本）
conda create -n simple-admin python=3.14

# 激活环境
conda activate simple-admin

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并修改配置：

```bash
cp .env.example .env
```

主要配置项：
- `DATABASE_URL` - PostgreSQL 连接字符串
- `REDIS_HOST` / `REDIS_PORT` / `REDIS_PASSWORD` - Redis 连接配置
- `REDIS_DB_SESSION` / `REDIS_DB_CACHE` / `REDIS_DB_TOKEN` - Redis 多数据库分离
- `JWT_SECRET_KEY` - JWT 密钥

### 3. 创建数据库

```sql
CREATE DATABASE simple_admin;
```

### 4. 运行数据库迁移

```bash
# 生成迁移文件
alembic revision --autogenerate -m "init"

# 执行迁移
alembic upgrade head
```

### 5. 初始化数据

```bash
python -m app.utils.init_data
```

### 6. 启动服务

```bash
# 开发模式
uvicorn main:app --reload --port 8000

# 或者直接运行
python main.py
```

### 7. 访问 API 文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 接口

### 认证接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/auth/captcha` | GET | 获取验证码 |
| `/api/auth/login` | POST | 登录 |
| `/api/auth/register` | POST | 注册 |
| `/api/auth/logout` | POST | 退出登录 |
| `/api/auth/refresh` | POST | 刷新Token |
| `/api/auth/codes` | GET | 获取权限码 |

### 用户接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/user/info` | GET | 获取用户信息 |
| `/api/user/list` | GET | 用户列表 |
| `/api/user` | POST | 创建用户 |
| `/api/user/{id}` | PUT | 更新用户 |
| `/api/user/{id}` | DELETE | 删除用户 |

### 角色接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/role/list` | GET | 角色列表 |
| `/api/role/all` | GET | 所有角色 |
| `/api/role/{id}` | GET | 角色详情 |
| `/api/role` | POST | 创建角色 |
| `/api/role/{id}` | PUT | 更新角色 |
| `/api/role/{id}` | DELETE | 删除角色 |

### 菜单接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/menu/all` | GET | 用户菜单（动态路由） |
| `/api/menu/list` | GET | 菜单列表 |
| `/api/menu/{id}` | GET | 菜单详情 |
| `/api/menu` | POST | 创建菜单 |
| `/api/menu/{id}` | PUT | 更新菜单 |
| `/api/menu/{id}` | DELETE | 删除菜单 |

### 日志接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/log/list` | GET | 日志列表 |
| `/api/log/{id}` | GET | 日志详情 |

## 响应格式

所有接口统一返回格式：

```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

## 默认账号

初始化数据后，默认创建超级管理员账号：

- 用户名: `admin`
- 密码: `admin123`

## 开发说明

### 添加新接口

本项目采用路由自动注册机制，只需：

1. 在 `app/models/` 创建数据库模型
2. 在 `app/schemas/` 创建 Pydantic 模型
3. 在 `app/api/` 创建路由文件（定义 `router` 变量即可自动注册）

详细说明请查看 [API 路由开发指南](../doc/API_ROUTER.md)

### 数据库迁移

```bash
# 修改模型后，生成迁移文件
alembic revision --autogenerate -m "描述"

# 执行迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```
