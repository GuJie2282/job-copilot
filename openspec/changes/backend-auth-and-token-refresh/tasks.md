# 实施任务清单

## 1. 后端项目初始化

- [x] 1.1 创建 `backend/` 目录结构
- [x] 1.2 创建 `backend/requirements.txt`，添加依赖（FastAPI、SQLAlchemy、passlib 等）
- [x] 1.3 创建 `backend/.env` 配置文件（数据库、JWT、环境变量）
- [x] 1.4 创建 `backend/src/__init__.py` 和 `backend/src/main.py`（FastAPI 应用入口）
- [x] 1.5 配置 CORS（允许前端 `http://localhost:3000` 访问）

## 2. 数据库模型设计

- [x] 2.1 创建 `backend/src/models/base.py`（SQLAlchemy Base 类）
- [x] 2.2 创建 `backend/src/models/user.py`（User、VerificationCode、RefreshToken 模型）
- [x] 2.3 创建 `backend/src/models/__init__.py`，导出所有模型
- [x] 2.4 配置数据库连接（SQLite）
- [x] 2.5 初始化 Alembic（数据库迁移工具）- 已用 init_db.py 替代
- [x] 2.6 创建第一个迁移（生成数据库表）- 已用 init_db.py 替代

## 3. Pydantic Schemas（请求/响应类型）

- [x] 3.1 创建 `backend/src/schemas/auth.py`（登录、注册、刷新请求/响应）
- [x] 3.2 创建 `backend/src/schemas/user.py`（用户信息响应）
- [x] 3.3 创建 `backend/src/schemas/__init__.py`，导出所有 Schemas

## 4. 核心安全功能

- [x] 4.1 创建 `backend/src/core/security.py`（密码哈希、JWT 生成/验证）
- [x] 4.2 实现密码哈希函数（使用 passlib + bcrypt）
- [x] 4.3 实现 JWT Token 生成函数（Access Token + Refresh Token）
- [x] 4.4 实现 JWT Token 验证函数
- [x] 4.5 创建 `backend/src/core/deps.py`（依赖注入：get_current_user）
- [x] 4.6 创建 `backend/src/core/__init__.py`

## 5. 业务逻辑层（Services）

- [x] 5.1 创建 `backend/src/services/auth_service.py`（认证服务）
- [x] 5.2 实现注册逻辑（验证码验证、密码哈希、创建用户）
- [x] 5.3 实现登录逻辑（密码验证、Token 生成）
- [x] 5.4 实现退出登录逻辑（删除 Refresh Token）
- [x] 5.5 实现刷新 Token 逻辑（验证 Refresh Token、生成新 Token）
- [x] 5.6 创建 `backend/src/services/code_service.py`（验证码服务）
- [x] 5.7 实现验证码生成逻辑（6 位随机数字）
- [x] 5.8 实现验证码发送逻辑（开发环境打印到控制台）
- [x] 5.9 实现验证码验证逻辑（检查有效期、未使用）
- [x] 5.10 创建 `backend/src/services/__init__.py`

## 6. 限流和中间件

- [x] 6.1 安装并配置 `slowapi`（限流库）
- [x] 6.2 创建 `backend/src/core/limiter.py`（限流配置）
- [x] 6.3 配置全局限流（如 100 次/分钟）
- [x] 6.4 为 `/auth/send-code` 端点配置特殊限流（5 次/分钟）

## 7. API 路由实现

- [x] 7.1 创建 `backend/src/api/__init__.py`
- [x] 7.2 创建 `backend/src/api/auth.py`（认证路由）
- [x] 7.3 实现 `POST /auth/register` 端点
- [x] 7.4 实现 `POST /auth/login` 端点
- [x] 7.5 实现 `POST /auth/send-code` 端点（带限流）
- [x] 7.6 实现 `POST /auth/logout` 端点
- [x] 7.7 实现 `POST /auth/refresh` 端点
- [x] 7.8 在 `main.py` 中注册认证路由

## 8. 前端 API 接口扩展

- [x] 8.1 在 `web/src/api/auth.ts` 中新增 `refreshToken()` 方法
- [x] 8.2 在 `web/src/types/user.ts` 中添加 `RefreshTokenRequest` 类型

## 9. 前端 Token 刷新逻辑

- [x] 9.1 修改 `web/src/api/client.ts` 响应拦截器
- [x] 9.2 添加 Token 刷新逻辑（401 错误时自动刷新）
- [x] 9.3 实现防重试机制（`_isRetry` 标记）
- [x] 9.4 处理刷新失败（清除 Token、跳转登录）

## 10. 前端用户状态优化

- [x] 10.1 修改 `web/src/stores/user.ts`，添加 Token 刷新方法
- [x] 10.2 优化登录/注册成功后的 Token 存储逻辑

## 11. 测试和调试

- [ ] 11.1 启动后端服务（`python backend/src/main.py`）
- [ ] 11.2 启动前端服务（`cd web && npm run dev`）
- [ ] 11.3 测试注册流程（发送验证码 → 注册 → 登录）
- [ ] 11.4 测试登录流程（邮箱密码登录）
- [ ] 11.5 测试 Token 刷新流程（等待 15 分钟或手动过期 Token）
- [ ] 11.6 测试退出登录流程
- [ ] 11.7 测试限流机制（频繁请求验证码）
- [ ] 11.8 测试验证码过期（超过 5 分钟后尝试使用）

## 12. 文档和清理

- [x] 12.1 创建 `backend/README.md`（后端项目说明）
- [x] 12.2 在主项目 `README.md` 中添加后端启动说明
- [x] 12.3 更新 `web/快速开始.md`，添加后端启动步骤
- [x] 12.4 清理临时文件和调试代码
- [x] 12.5 验证所有代码符合 Python 和 Vue 3 规范

## 13. 可选优化（延后）

- [ ] 13.1 添加图形验证码（防刷验证码接口）
- [ ] 13.2 实现邮件真实发送（生产环境）
- [ ] 13.3 将 Refresh Token 改为 HttpOnly Cookie 存储
- [ ] 13.4 添加用户画像（Profile）API 端点
- [ ] 13.5 添加数据库迁移到 PostgreSQL 的配置示例
