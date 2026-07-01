# 技术设计：后端登录注册模块与 Token 刷新机制

## Context

### 当前状态

求职 Copilot 项目是一个基于 LangGraph 的 AI 求职 Agent，目前**仅有前端登录注册界面**（Vue 3 + TypeScript + Element Plus），缺少后端认证服务。

**前端现状：**
- ✅ 登录页面（`/login`）、注册页面（`/register`）、首页（`/`）已完成
- ✅ 前端已定义 API 接口格式（`LoginCredentials`、`RegisterData`、`LoginResponse`）
- ✅ Axios 拦截器已配置，但 401 时直接跳转登录页（缺少刷新逻辑）
- ✅ 用户状态管理使用 Pinia，Token 存储在 localStorage

**后端现状：**
- ❌ 完全没有后端 API 服务
- ❌ 无数据库、无认证逻辑、无安全机制
- ✅ 项目已有 Python 环境（LangGraph + LangChain）

**约束条件：**
- 这是**个人面试作品集项目**，非商业生产环境
- 负责人技术背景较弱（AI PM 方向），需要代码多注释、易于理解
- 需要展示**全栈能力**和**技术选型思考**（面试加分项）
- 暂不引入 Redis、Celery 等复杂组件（可选组件延后）

### 为什么需要设计文档

本变更涉及：
1. **跨模块变更**：前端 + 后端 + 数据库
2. **新增外部依赖**：FastAPI、SQLAlchemy、passlib 等
3. **安全机制**：密码哈希、JWT、限流、验证码
4. **数据模型设计**：三个新表

需要在编码前明确技术决策和架构方案。

## Goals / Non-Goals

### Goals

**核心目标：**
1. ✅ 实现完整的后端认证服务（注册、登录、退出、验证码）
2. ✅ 实现 Token 刷新机制，提升用户体验（减少重复登录）
3. ✅ 建立安全的数据存储和传输机制（密码哈希、JWT）
4. ✅ 提供清晰的 API 接口，与前端契约匹配
5. ✅ 代码易于理解和维护，适合面试讲解

**技术目标：**
- 使用现代 Python 技术栈（FastAPI）
- 遵循 RESTful API 设计规范
- 实现基本的安全防护（限流、CORS、SQL 注入防护）
- 支持开发环境的快速迭代（SQLite、控制台打印验证码）

### Non-Goals

**明确排除（不在本次实现范围）：**
- ❌ 第三方登录（微信、GitHub 等）- 前端有入口，但后端暂不实现
- ❌ "记住我" 功能 - 前端有 checkbox，但后端暂不实现
- ❌ 图形验证码 - 仅用限流防刷
- ❌ 多设备管理 - 单设备登录（踢出其他设备）
- ❌ 邮箱真实验证 - 开发环境打印到控制台
- ❌ Redis 缓存 - 使用 SQLite 存储验证码
- ❌ 异步任务队列 - 同步发送邮件（或打印）
- ❌ 用户权限系统（免费/付费）- 后续迭代

## Decisions

### 决策 1：后端框架选择 FastAPI

**选项对比：**

| 框架 | 优势 | 劣势 | 评分 |
|------|------|------|------|
| **FastAPI** | 现代异步、自动文档、类型验证 | 相对新 | ⭐⭐⭐⭐⭐ |
| Flask | 轻量灵活、生态成熟 | 手动配置多 | ⭐⭐⭐ |
| Django | 功能全面、安全性好 | 过重、学习曲线陡 | ⭐⭐ |

**选择理由：**
1. **与 LangChain 生态契合** - 都是现代 Python 库，易于集成
2. **自动生成 OpenAPI 文档** - 前端对接方便，面试可讲"API First"
3. **异步支持** - AI 调用不阻塞，为未来扩展做准备
4. **类型安全** - Pydantic 自动验证，减少运行时错误
5. **面试加分项** - 可讲"为什么选 FastAPI 而非 Django"

**示例：**
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/auth/login")
async def login(req: LoginRequest):
    # Pydantic 自动验证 email 和 password 字段
    # 自动生成 OpenAPI 文档
    pass
```

### 决策 2：密码哈希使用 passlib + bcrypt

**选项对比：**

| 方案 | 优势 | 劣势 | 安全性 |
|------|------|------|--------|
| **MD5/SHA-256** | 快速 | ❌ 可被彩虹表攻击 | 🔴 不安全 |
| Argon2 | 内存困难、抗 GPU 破解 | 需额外依赖 | 🟢 最佳 |
| **bcrypt** | 广泛使用、可调参数 | Python 实现较慢 | 🟢 推荐 |
| passlib | 成熟稳定、API 简单 | - | 🟢 推荐 |

**选择理由：**
1. **成熟稳定** - Python 生态标准，社区支持好
2. **API 简洁** - 三行代码完成哈希和验证
3. **向后兼容** - 未来可切换到 Argon2（passlib 支持）
4. **面试可讲** - "为什么不用 MD5/SHA-256"

**实现示例：**
```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 哈希密码
hash = pwd_context.hash("user_password")  # $2b$12$...

# 验证密码
is_valid = pwd_context.verify("user_password", hash)
```

### 决策 3：数据库使用 SQLite（开发）/ PostgreSQL（生产预留）

**选项对比：**

| 数据库 | 优势 | 劣势 | 适用场景 |
|--------|------|------|----------|
| **SQLite** | 零配置、文件存储、够用 | 并发弱、无网络访问 | 开发/小规模 |
| PostgreSQL | 功能强大、并发好 | 需独立服务 | 生产环境 |
| MongoDB | 灵活文档模型 | Schema 弱 | 数据复杂场景 |

**选择理由：**
1. **零配置** - 无需安装数据库服务，`python main.py` 即可运行
2. **够用** - 个人作品集项目，并发量极低
3. **易于迁移** - SQLAlchemy ORM，一行配置切换到 PostgreSQL
4. **面试可讲** - "为什么 SQLite 足够，什么场景需要 PostgreSQL"

**配置切换：**
```python
# 开发环境
SQLALCHEMY_DATABASE_URL = "sqlite:///./job_copilot.db"

# 生产环境（切换到 PostgreSQL）
# SQLALCHEMY_DATABASE_URL = "postgresql://user:pass@localhost/dbname"
```

### 决策 4：JWT 双 Token 机制（Access + Refresh）

**Token 设计：**

```
┌─────────────────────────────────────────────────────────┐
│                  JWT Token 架构                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Access Token（短期）                                    │
│  ├─ 有效期：15 分钟                                      │
│  ├─ 存储：localStorage                                    │
│  ├─ 用途：每次 API 请求携带                              │
│  └─ Payload：{user_id, email, exp, iat}                 │
│                                                         │
│  Refresh Token（长期）                                   │
│  ├─ 有效期：7 天                                         │
│  ├─ 存储：localStorage（当前）→ HttpOnly Cookie（优化）   │
│  ├─ 用途：刷新 Access Token                             │
│  └─ Payload：{user_id, token_id, exp}                  │
│                                                         │
│  刷新流程：                                              │
│  1. Access Token 过期 → 401 错误                        │
│  2. 前端拦截器捕获 401                                   │
│  3. 调用 POST /auth/refresh（携带 refresh_token）        │
│  4. 后端验证 refresh_token，返回新的 access_token        │
│  5. 前端重试原请求                                        │
│  6. 刷新失败（refresh_token 也过期）→ 跳转登录页          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**选择理由：**
1. **安全性** - Access Token 短期有效，降低泄露风险
2. **用户体验** - Refresh Token 长期有效，减少重复登录
3. **行业标准** - OAuth 2.0 标准实践
4. **前端已预留** - 前端已存储 refreshToken，只需加刷新逻辑

### 决策 5：验证码存储在 SQLite（暂不用 Redis）

**选项对比：**

| 方案 | 优势 | 劣势 | 选择 |
|------|------|------|------|
| **SQLite** | 零依赖、够用 | 需定时清理 | ✅ 选用 |
| Redis | 自动过期、性能好 | 多一个依赖 | ❌ 延后 |

**选择理由：**
1. **减少依赖** - 避免引入 Redis，简化部署
2. **够用** - 验证码量极小，SQLite 性能足够
3. **简单迁移** - 后续可无缝切换到 Redis

**数据清理策略：**
```python
# 方案 A：应用启动时清理
@app.on_event("startup")
async def cleanup_expired_codes():
    """启动时清理过期验证码"""
    db.query(VerificationCode).filter(
        VerificationCode.expires_at < datetime.now()
    ).delete()

# 方案 B：定时任务（简单版）
# 每次生成验证码时，先清理该邮箱的旧验证码
```

### 决策 6：限流使用 slowapi（而非手动实现）

**为什么需要限流：**
- 防止验证码接口被刷（DDoS 攻击）
- 防止同一邮箱频繁发送
- 保护数据库和邮件服务

**选择 slowapi 的理由：**
1. **装饰器语法** - 一行代码实现限流
2. **灵活配置** - 支持全局/单端点限流
3. **自动响应** - 超限时返回 429 状态码

**实现示例：**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/auth/send-code")
@limiter.limit("5/minute")  # 每分钟最多5次
async def send_code():
    pass
```

### 决策 7：前端 Token 刷新在 Axios 拦截器实现

**实现位置：**
- ❌ 不在每个 API 调用处处理（代码重复）
- ❌ 不在 Pinia store 处理（不透明）
- ✅ **在 Axios 响应拦截器**（统一处理）

**刷新逻辑：**
```typescript
// 当前实现（需要修改）
if (error.response?.status === 401) {
  localStorage.removeItem('token');
  router.push('/login');  // 直接跳转
}

// 改进后
if (error.response?.status === 401 && !error._isRetry) {
  try {
    const newToken = await authApi.refreshToken(refreshToken);
    localStorage.setItem('token', newToken);
    error.config.headers['Authorization'] = `Bearer ${newToken}`;
    return client(error.config);  // 重试原请求
  } catch {
    localStorage.clear();
    router.push('/login');
  }
}
```

**选择理由：**
1. **统一处理** - 所有 API 调用自动受益
2. **透明** - 业务代码无感知
3. **防重试** - 用 `_isRetry` 标记避免死循环

## Risks / Trade-offs

### 风险 1：Refresh Token 泄露风险

**风险描述：**
当前设计将 Refresh Token 存储在 localStorage，容易被 XSS 攻击窃取。

**缓解措施：**
1. [短期] Refresh Token 设置短有效期（7 天）
2. [短期] 后端记录 Refresh Token 的设备信息（IP、User-Agent）
3. [长期] 改用 HttpOnly Cookie 存储（前端无 JavaScript 访问权限）

**Trade-off：**
- 安全性 vs 开发复杂度 - HttpOnly Cookie 需要后端配置 CORS credentials

### 风险 2：验证码被绕过

**风险描述：**
用户可能通过以下方式绕过验证码：
1. 刷新页面重置倒计时
2. 修改前端代码
3. 用多个邮箱刷验证码

**缓解措施：**
1. ✅ **后端限流** - 每分钟 5 次，全局限流 + 用户级限流
2. ✅ **验证码有效期** - 5 分钟过期
3. ✅ **使用即销毁** - 验证码一次性使用
4. ⚠️ 图形验证码（延后 - 复杂度高）

### 风险 3：SQLite 并发限制

**风险描述：**
SQLite 不支持高并发写入，可能导致数据库锁死。

**缓解措施：**
1. ✅ **够用即可** - 个人项目，并发量极低
2. ✅ **快速切换** - SQLAlchemy ORM，一行配置切换到 PostgreSQL
3. 📋 **监控** - 添加日志监控数据库锁等待时间

**Trade-off：**
- 简单性 vs 并发性能 - 当前选择简单性，生产环境可切换

### 风险 4：JWT Secret 泄露

**风险描述：**
JWT Secret 硬编码在代码中，泄露后攻击者可伪造任意 Token。

**缓解措施：**
1. ✅ **环境变量** - `JWT_SECRET_KEY` 从 `.env` 读取
2. ✅ **.gitignore** - 确保 `.env` 不提交
3. ✅ **强随机 Secret** - 生成 32 字节随机字符串
4. 📋 **密钥轮换** - 定期更换 Secret（生产环境）

### 风险 5：前后端契约不一致

**风险描述：**
前端定义的 API 格式与后端实现不匹配，导致对接失败。

**缓解措施：**
1. ✅ **OpenAPI 文档** - FastAPI 自动生成，前端可参考
2. ✅ **类型同步** - 后端 Pydantic Model 与前端 TypeScript 类型保持一致
3. ✅ **集成测试** - 后端实现后，用前端真实测试一遍

## Migration Plan

### 部署步骤

**阶段 1：后端开发（独立）**
```bash
# 1. 创建后端项目
mkdir backend
cd backend
pip install fastapi uvicorn sqlalchemy passlib python-jose

# 2. 实现核心 API
# - POST /auth/register
# - POST /auth/login
# - POST /auth/send-code
# - POST /auth/refresh
# - POST /auth/logout

# 3. 启动后端服务
python src/main.py  # http://localhost:8000
```

**阶段 2：前后端联调**
```bash
# 1. 启动后端
cd backend && python src/main.py

# 2. 启动前端（另一个终端）
cd web && npm run dev  # http://localhost:3000

# 3. 测试完整流程
# - 注册 → 登录 → 访问首页 → 退出登录
# - Token 过期后自动刷新
```

**阶段 3：生产构建（可选）**
```bash
# 前端构建
cd web && npm run build

# 后端打包（可选，可用 Docker）
docker build -t job-copilot-backend .
```

### 回滚策略

**后端回滚：**
```bash
# 如果后端有问题，前端可继续使用 Mock 数据
# 修改 web/src/api/auth.ts，使用 mock 数据
```

**前端回滚：**
```bash
# 如果前端拦截器有问题，回退到直接跳转登录
git checkout HEAD~1 web/src/api/client.ts
```

### 环境变量配置

**`.env` 文件（后端）：**
```bash
# 数据库
DATABASE_URL=sqlite:///./job_copilot.db

# JWT
JWT_SECRET_KEY=your-32-byte-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# 邮件（生产环境）
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# 环境
ENV=development  # development | production
```

## Open Questions

### Q1: 是否需要图形验证码？

**当前决策：** 否，仅用限流防刷。

**原因：**
- 开发复杂度高（需要 Canvas 或第三方库）
- 用户体验稍差（需要识别图形）
- 限流（5 次/分钟）已足够防护

**后续考虑：** 如果验证码接口被刷，再添加。

### Q2: 是否需要手机号验证码？

**当前决策：** 仅邮箱验证码，手机号字段可选。

**原因：**
- 手机号需要接入短信服务（成本高）
- 邮箱验证码已满足需求

### Q3: 是否支持多设备登录？

**当前决策：** 单设备登录（新登录踢出旧设备）。

**实现：**
```python
# 用户登录时，删除该用户的旧 refresh_token
db.query(RefreshToken).filter_by(user_id=user.id).delete()
db.add(RefreshToken(user_id=user.id, token=new_token))
```

**后续扩展：** 支持多设备，需要在 refresh_tokens 表加 device_id 字段。

### Q4: 生产环境数据库选型？

**当前决策：** 开发用 SQLite，生产预留 PostgreSQL 切换。

**切换成本：** 一行配置 + 修改连接 URL。

---

**面试讲点总结：**

1. **技术选型** - 为什么 FastAPI 而不是 Django？为什么 SQLite 而不是 MongoDB？
2. **安全设计** - 为什么用 bcrypt 而不是 MD5？为什么 JWT 双 Token？
3. **权衡决策** - Refresh Token 存储位置（localStorage vs Cookie）、验证码防刷（限流 vs 图形验证码）
4. **可扩展性** - 如何从 SQLite 切换到 PostgreSQL？如何加图形验证码？
