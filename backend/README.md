# 求职 Copilot 后端服务

基于 FastAPI 的 AI 求职教练后端服务，提供用户认证、JD 匹配、简历优化等 API。

## 技术栈

- **FastAPI** - 现代化 Python Web 框架
- **SQLAlchemy** - ORM 数据库操作
- **SQLite** - 轻量级数据库（开发环境）
- **Pydantic** - 数据验证
- **passlib** - 密码哈希（bcrypt）
- **python-jose** - JWT 处理
- **slowapi** - API 限流

## 快速开始

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 配置环境变量

已提供 `.env` 文件，包含默认配置：

```bash
# 数据库
DATABASE_URL=sqlite:///./job_copilot.db

# JWT
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production-min-32-chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# 环境
ENV=development

# CORS
FRONTEND_URL=http://localhost:3000

# 限流
RATE_LIMIT_GLOBAL="100/minute"
RATE_LIMIT_SEND_CODE="5/minute"
```

⚠️ **生产环境请修改 `JWT_SECRET_KEY` 为强随机字符串！**

### 3. 初始化数据库

```bash
# 方法 1：使用 Python 脚本（推荐）
python -c "from src.models.base import Base, engine; Base.metadata.create_all(bind=engine); print('数据库初始化完成')"

# 方法 2：使用 Alembic（需要先安装）
# alembic upgrade head
```

### 4. 启动服务

```bash
# 开发模式（支持热重载）
python src/main.py

# 或使用 uvicorn
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

服务将在 **http://localhost:8000** 启动

### 5. 访问文档

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **健康检查**: http://localhost:8000/health

## API 端点

### 认证接口（`/auth/*`）

| 方法 | 端点 | 描述 | 是否需要认证 |
|------|------|------|--------------|
| POST | `/auth/register` | 用户注册 | ❌ |
| POST | `/auth/login` | 用户登录 | ❌ |
| POST | `/auth/send-code` | 发送验证码 | ❌ |
| POST | `/auth/logout` | 退出登录 | ✅ |
| POST | `/auth/refresh` | 刷新 Token | ❌ |

### 其他端点

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/` | API 根路径 |
| GET | `/health` | 健康检查 |

## 项目结构

```
backend/
├── src/
│   ├── main.py              # FastAPI 应用入口
│   ├── models/              # 数据库模型
│   │   ├── base.py          # SQLAlchemy Base 类
│   │   └── user.py          # User, VerificationCode, RefreshToken
│   ├── schemas/             # Pydantic 数据模型
│   │   ├── auth.py          # 认证请求/响应
│   │   └── user.py          # 用户信息
│   ├── core/                # 核心功能
│   │   ├── security.py      # 密码哈希 + JWT
│   │   ├── deps.py          # 依赖注入
│   │   └── limiter.py       # API 限流
│   ├── services/            # 业务逻辑
│   │   ├── auth_service.py  # 认证服务
│   │   └── code_service.py  # 验证码服务
│   └── api/                 # API 路由
│       └── auth.py          # 认证路由
├── requirements.txt         # Python 依赖
├── .env                     # 环境变量
└── README.md               # 本文件
```

## 核心功能

### ✅ 用户认证
- 邮箱 + 密码登录
- 邮箱验证码注册
- JWT Token 认证
- Refresh Token 自动刷新

### ✅ 安全机制
- 密码 bcrypt 哈希（成本因子 12）
- JWT Token 签名验证
- API 限流（防 DDoS）
- CORS 跨域保护

### ✅ 验证码系统
- 6 位数字验证码
- 5 分钟有效期
- 一次性使用
- 开发环境打印到控制台

## 开发指南

### 添加新的 API 端点

1. 在 `src/schemas/` 创建请求/响应模型
2. 在 `src/services/` 创建业务逻辑
3. 在 `src/api/` 创建路由
4. 在 `src/main.py` 注册路由

示例：

```python
# src/api/users.py
from fastapi import APIRouter, Depends
from src.core.deps import get_current_user

user_router = APIRouter()

@user_router.get("/me")
async def get_profile(current_user = Depends(get_current_user)):
    return current_user
```

### 数据库操作

使用 SQLAlchemy ORM：

```python
from src.models.base import get_db
from src.models.user import User
from sqlalchemy.orm import Session

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()
```

### 环境变量

使用 `python-dotenv` 读取：

```python
import os
from dotenv import load_dotenv

load_dotenv()
secret_key = os.getenv("JWT_SECRET_KEY")
```

## 生产部署

### 1. 修改配置

```bash
# .env
ENV=production
DATABASE_URL=postgresql://user:pass@localhost/dbname
JWT_SECRET_KEY=<强随机字符串>
```

### 2. 切换数据库

修改 `DATABASE_URL` 为 PostgreSQL，无需改代码：

```python
# SQLite
DATABASE_URL=sqlite:///./job_copilot.db

# PostgreSQL
DATABASE_URL=postgresql://user:pass@localhost/dbname
```

### 3. 使用 Gunicorn 运行

```bash
pip install gunicorn
gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

### 4. Docker 部署（可选）

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "src.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker"]
```

## 常见问题

### Q: 如何重置数据库？

```bash
rm job_copilot.db
python -c "from src.models.base import Base, engine; Base.metadata.create_all(bind=engine)"
```

### Q: 如何查看验证码？

开发环境，验证码会打印到后端控制台：

```
==================================================
📧 验证码发送到: zhangsan@example.com
🔢 验证码: 123456
⏰ 有效期: 5 分钟
==================================================
```

### Q: Token 默认有效期是多少？

- **Access Token**: 15 分钟
- **Refresh Token**: 7 天

可在 `.env` 修改：

```bash
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30
```

### Q: 如何测试 API？

使用 Swagger UI（http://localhost:8000/docs）或 curl：

```bash
# 发送验证码
curl -X POST http://localhost:8000/auth/send-code \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'

# 登录
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}'
```

## 许可证

MIT
