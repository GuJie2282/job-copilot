# 变更提案：后端登录注册模块并优化前端Token刷新机制

## Why

求职 Copilot 项目目前仅有前端登录注册界面，缺少后端认证服务。用户无法真正完成登录注册流程，且前端 Token 过期后会直接跳转登录页，用户体验差。

**核心问题：**
1. ❌ 没有后端 API，前端无法完成真实的认证流程
2. ❌ Token 过期后无刷新机制，用户被迫频繁登录
3. ❌ 缺少密码哈希、JWT 管理、验证码等安全机制

**为什么现在做：**
- 前端登录注册模块已完成，是实施后端的最佳时机
- 认证是系统的基础能力，其他功能（JD匹配、简历优化）都依赖它
- 个人作品集项目需要展示全栈能力

## What Changes

### 后端（新增）

**新增 FastAPI 认证服务：**
- ✅ 实现用户注册 API (`POST /auth/register`)
  - 邮箱验证码验证
  - 密码哈希存储（bcrypt）
  - 返回 JWT Token
- ✅ 实现用户登录 API (`POST /auth/login`)
  - 邮箱密码验证
  - 生成 Access Token + Refresh Token
- ✅ 实现验证码发送 API (`POST /auth/send-code`)
  - 生成 6 位数字验证码
  - 开发环境打印到控制台，生产环境发送邮件
  - 限流保护（5次/分钟）
- ✅ 实现 Token 刷新 API (`POST /auth/refresh`)
  - 验证 Refresh Token
  - 颁发新的 Access Token
- ✅ 实现退出登录 API (`POST /auth/logout`)
  - 清除 Refresh Token

**数据库设计（SQLite）：**
- ✅ `users` 表 - 用户基本信息
- ✅ `verification_codes` 表 - 验证码记录
- ✅ `refresh_tokens` 表 - 刷新令牌管理

**安全机制：**
- ✅ 密码使用 bcrypt 哈希（passlib）
- ✅ JWT 签名验证（python-jose）
- ✅ API 限流（slowapi）
- ✅ CORS 跨域支持

### 前端（修改）

**API 客户端优化：**
- ✅ 新增 `refreshToken()` API 接口
- ✅ 改造响应拦截器：401 时先尝试刷新 Token
- ✅ Token 刷新失败才跳转登录页

**类型定义：**
- ✅ 新增 `RefreshTokenRequest` 类型

**用户状态管理：**
- ✅ 优化 Token 刷新逻辑（Pinia store）

## Capabilities

### New Capabilities

- **`user-authentication`**: 用户认证能力
  - 用户注册（验证码验证）
  - 用户登录（邮箱密码）
  - 退出登录
  - 邮箱验证码发送
  - 密码哈希存储
  - JWT Token 颁发与验证

- **`token-refresh`**: Token 刷新能力
  - Refresh Token 机制
  - Token 过期自动刷新
  - 前端拦截器集成
  - 刷新失败处理

### Modified Capabilities

无现有能力的需求级变更。

## Impact

**新增依赖：**
- FastAPI、SQLAlchemy、Pydantic、Alembic
- passlib[bcrypt]、python-jose
- slowapi、fastapi-mail

**新增代码：**
- `backend/` 目录（完整后端项目）
  - API 路由、数据模型、业务逻辑
- `web/src/api/auth.ts` - 新增刷新接口
- `web/src/api/client.ts` - 拦截器改造
- `web/src/stores/user.ts` - Token 刷新逻辑

**运行时影响：**
- 需要同时运行前端（`npm run dev`）和后端（`python src/main.py`）
- 后端默认监听 `http://localhost:8000`
- 前端通过代理访问后端 API

**数据迁移：**
- 无（全新功能，无现成用户数据）
