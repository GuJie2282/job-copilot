## Context

### 当前状态

认证系统（backend-auth-and-token-refresh）已实现基本功能，但存在以下技术债务：

1. **数据层**：使用 SQLAlchemy + SQLite，所有数据库操作缺少事务保护
2. **业务层**：auth_service.py 中多步操作（验证码验证→用户创建→Token生成）失败时无回滚
3. **API层**：错误响应格式不统一，缺少详细错误码和用户友好消息
4. **日志**：仅有 print() 调试日志，缺少结构化日志和关键路径覆盖
5. **测试**：完全缺失测试，重构风险高

### 约束条件

- **开发环境**：SQLite 数据库（生产环境应升级为 PostgreSQL）
- **技术栈**：FastAPI + SQLAlchemy + Pydantic + Vue3 + TypeScript
- **团队背景**：负责人技术薄弱，需要详细的中文注释和渐进式改进
- **时间压力**：这是求职面试作品集项目，需要尽快交付高质量版本

### 利益相关者

- **求职者（用户）**：需要稳定、友好的认证体验
- **项目负责人**：需要可维护、可扩展的代码，能作为面试作品展示
- **面试官**：关注工程实践、错误处理、测试覆盖率

## Goals / Non-Goals

**Goals:**

1. **数据一致性**：所有认证操作使用数据库事务，确保原子性
2. **错误友好性**：统一错误响应格式，提供清晰的错误码和操作指引
3. **可观测性**：添加结构化日志，覆盖关键路径，便于问题排查
4. **测试覆盖**：单元测试 + 集成测试覆盖核心认证流程
5. **API 契约一致性**：统一前后端字段命名，消除接口不匹配问题

**Non-Goals:**

- **生产环境优化**：暂不涉及 Redis 缓存、分布式事务等高级特性
- **安全增强**：暂不添加登录失败锁定、2FA 等高级安全特性（未来扩展）
- **数据库迁移**：暂不更换数据库（保持 SQLite，简化开发）
- **前端重构**：仅调整认证相关代码，不重构整体前端架构

## Decisions

### 1. 错误处理体系设计

**决策**：建立结构化错误响应格式，包含错误码、用户消息、建议操作

**方案对比**：

| 方案 | 优点 | 缺点 | 选择 |
|------|------|------|------|
| 简单字符串 | 实现简单 | 信息不足、前端难以解析 | ❌ |
| 错误码枚举 | 类型安全、IDE友好 | 需要维护映射关系 | ✅ |
| 国际化消息 | 支持多语言 | 当前项目不需要 | ❌ |

**选型理由**：

```python
# 统一错误响应格式
class ErrorResponse(BaseModel):
    code: str           # 错误码（如 AUTH_EMAIL_EXISTS）
    message: str        # 用户友好的中文消息
    details: Optional[Dict] = None  # 详细信息（仅开发环境）
    action: Optional[str] = None     # 建议操作（如 "login"）

# 使用示例
{
  "code": "AUTH_EMAIL_EXISTS",
  "message": "该邮箱已被注册，请直接登录",
  "action": "login"
}
```

**前端处理**：

```typescript
// 根据错误码和 action 自动处理
if (error.code === 'AUTH_EMAIL_EXISTS' && error.action === 'login') {
  showLoginModal();  // 自动引导用户登录
}
```

### 2. 数据库事务边界设计

**决策**：按业务逻辑划分事务边界，每个事务包含完整的业务单元

**事务边界划分**：

```
注册流程：
  事务1: 验证码验证 + 标记已使用
  事务2: 用户创建 + 数据持久化
  非事务: Token生成（JWT无需数据库）

登录流程：
  事务1: 用户查询 + 密码验证 + Token存储 + 登录时间更新

Token刷新流程：
  事务1: 旧Token验证 + 删除 + 新Token生成 + 存储
```

**实现方式**：

```python
# 方案对比
# 1. 手动事务控制
db.begin()
try:
    # 业务逻辑
    db.commit()
except:
    db.rollback()
    raise

# 2. 上下文管理器（推荐）
with db.begin():  # 自动提交或回滚
    # 业务逻辑
```

**选择理由**：上下文管理器更简洁、自动回滚、代码更清晰

### 3. 错误码体系设计

**决策**：采用模块化错误码，按功能域划分

**错误码命名规范**：

```
格式: <DOMAIN>_<ERROR>_<DETAIL>

示例:
  AUTH_EMAIL_EXISTS      (认证域-邮箱已存在)
  CODE_EXPIRED            (验证码域-已过期)
  TOKEN_INVALID           (Token域-无效)
  VALID_EMAIL_FORMAT      (验证域-邮箱格式错误)
```

**完整错误码列表**：

```python
class ErrorCode(str, Enum):
    # 认证错误 (AUTH_*)
    AUTH_EMAIL_EXISTS = "AUTH_EMAIL_EXISTS"
    AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
    AUTH_ACCOUNT_DISABLED = "AUTH_ACCOUNT_DISABLED"

    # 验证码错误 (CODE_*)
    CODE_INVALID = "CODE_INVALID"
    CODE_EXPIRED = "CODE_EXPIRED"
    CODE_ALREADY_USED = "CODE_ALREADY_USED"
    CODE_RECENTLY_SENT = "CODE_RECENTLY_SENT"

    # Token 错误 (TOKEN_*)
    TOKEN_INVALID = "TOKEN_INVALID"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_MISSING = "TOKEN_MISSING"

    # 验证错误 (VALID_*)
    VALID_EMAIL_FORMAT = "VALID_EMAIL_FORMAT"
    VALID_PASSWORD_TOO_SHORT = "VALID_PASSWORD_TOO_SHORT"
    VALID_PASSWORD_TOO_LONG = "VALID_PASSWORD_TOO_LONG"
    VALID_PHONE_FORMAT = "VALID_PHONE_FORMAT"

    # 系统错误 (SYSTEM_*)
    SYSTEM_DATABASE_ERROR = "SYSTEM_DATABASE_ERROR"
    SYSTEM_INTERNAL_ERROR = "SYSTEM_INTERNAL_ERROR"
```

### 4. 结构化日志设计

**决策**：使用 Python 标准库 logging 模块，采用结构化格式

**日志级别使用规范**：

```
DEBUG: 详细调试信息（开发环境）
INFO:  关键操作成功（用户注册、登录）
WARNING: 业务异常（验证码错误、密码错误）
ERROR: 系统错误（数据库异常、外部服务失败）
CRITICAL: 严重错误（服务不可用）
```

**日志格式设计**：

```python
# 结构化日志示例
logger.info(
    "user_register_success",
    extra={
        "user_id": str(user.id),
        "email": user.email,
        "ip": request.client.host
    }
)

# 输出格式（JSON）
{
  "timestamp": "2025-01-01T10:00:00Z",
  "level": "INFO",
  "event": "user_register_success",
  "user_id": "123",
  "email": "test@example.com",
  "ip": "127.0.0.1"
}
```

**敏感信息脱敏**：

```python
# 密码、Token等敏感信息不记录日志
logger.info("user_login", email=email)  # ✅ 不记录密码
logger.debug("token_generated", token=mask_token(token))  # ✅ 脱敏
```

### 5. 测试策略设计

**决策**：采用测试金字塔，单元测试为主，集成测试为辅

**测试覆盖范围**：

```
tests/
├── unit/                      # 单元测试（70%）
│   ├── test_security.py       # 密码哈希、JWT生成/验证
│   ├── test_code_service.py   # 验证码逻辑
│   ├── test_auth_service.py   # 认证业务逻辑
│   └── test_error_handler.py  # 错误处理
│
├── integration/               # 集成测试（20%）
│   ├── test_register_flow.py # 完整注册流程
│   ├── test_login_flow.py     # 完整登录流程
│   └── test_token_refresh.py  # Token刷新流程
│
└── e2e/                       # 端到端测试（10%）
    └── test_full_auth_flow.py # 注册→登录→刷新→登出
```

**关键测试用例**：

1. **注册流程**：
   - ✅ 正常注册成功
   - ✅ 邮箱已存在
   - ✅ 验证码无效
   - ✅ 验证码过期
   - ✅ 验证码已使用
   - ✅ 事务回滚（用户创建失败）

2. **登录流程**：
   - ✅ 正常登录成功
   - ✅ 用户不存在
   - ✅ 密码错误
   - ✅ 账户禁用
   - ✅ Token生成成功

3. **Token刷新**：
   - ✅ 正常刷新成功
   - ✅ Token无效
   - ✅ Token过期
   - ✅ 并发刷新处理

**测试框架选择**：

- **pytest**：功能强大、插件丰富、社区活跃
- **pytest-asyncio**：支持异步测试
- **pytest-cov**：测试覆盖率报告
- **httpx**：异步HTTP客户端（用于API测试）

### 6. 前后端字段命名规范

**决策**：后端统一使用 snake_case，前端使用 camelCase，API 层自动转换

**转换逻辑**：

```typescript
// 前端 → 后端（请求时）
{
  verificationCode: "123456"  // camelCase
}
↓ 转换
{
  verification_code: "123456"  // snake_case
}

// 后端 → 前端（响应时）
{
  refresh_token: "xyz..."  // snake_case
}
↓ 转换
{
  refreshToken: "xyz..."  // camelCase
}
```

**实现位置**：

```typescript
// web/src/api/auth.ts
const payload = {
  ...rest,
  verification_code: data.verificationCode  // 转换
};
```

### 7. Token刷新并发处理

**决策**：前端使用队列机制，避免并发刷新请求

**问题场景**：

```
时间线：
T0: 请求A失败（401）→ 触发刷新
T1: 请求B失败（401）→ 触发刷新  ← 并发刷新！
T2: 刷新A成功
T3: 刷新B成功（覆盖A）→ Token不一致
```

**解决方案**：

```typescript
// 请求队列 + 状态标记
let isRefreshing = false;
let refreshSubscribers: Array<(token: string) => void> = [];

function subscribeTokenRefresh(cb: (token: string) => void) {
  refreshSubscribers.push(cb);
}

// 队列处理
if (!isRefreshing) {
  isRefreshing = true;
  try {
    const newToken = await refreshAccessToken();
    refreshSubscribers.forEach(cb => cb(newToken));  // 通知所有等待的请求
  } finally {
    isRefreshing = false;
    refreshSubscribers = [];
  }
} else {
  // 等待刷新完成
  await new Promise(resolve => {
    subscribeTokenRefresh(token => {
      resolve(token);
    });
  });
}
```

## Risks / Trade-offs

### 风险1: SQLite 并发事务限制

**风险**：SQLite 在高并发写入时可能锁定数据库，影响性能

**缓解措施**：

- 当前项目为演示项目，用户量小，SQLite 足够
- 使用 WAL 模式（Write-Ahead Logging）提升并发性能
- 生产环境升级为 PostgreSQL（已预留迁移路径）

### 风险2: 错误码维护成本

**风险**：错误码体系增加维护复杂度，新增错误需要更新错误码

**缓解措施**：

- 建立错误码注册表（src/core/error_codes.py）
- 添加单元测试验证错误码唯一性
- 定期审查和清理未使用的错误码

### 风险3: 事务嵌套复杂性

**风险**：复杂的事务嵌套可能导致死锁或性能问题

**缓解措施**：

- 保持事务边界清晰，避免嵌套事务
- 每个事务只包含必要的数据库操作
- 添加事务超时保护（5秒超时）

### 风险4: 测试覆盖不足

**风险**：测试可能无法覆盖所有边界情况，遗漏Bug

**缓解措施**：

- 使用 pytest-cov 监控测试覆盖率（目标 >80%）
- 定期代码审查，补充边界测试用例
- 集成 CI/CD 自动运行测试

### 权衡1: 错误消息详细程度 vs 安全性

**权衡**：详细错误消息便于用户理解，但可能泄露系统信息

**平衡方案**：

```
开发环境：显示详细错误信息（堆栈、SQL语句）
生产环境：显示用户友好消息，详细日志记录到服务器
```

### 权衡2: 日志详细程度 vs 性能

**权衡**：详细日志便于调试，但可能影响性能

**平衡方案**：

```
INFO 级别：记录关键操作（性能影响小）
DEBUG 级别：仅在开发环境启用
生产环境：使用异步日志（如 loguru）
```

## Migration Plan

### 部署步骤

#### 阶段1: 后端优化（1-2天）

1. **创建错误处理基础设施**
   - 实现 `ErrorResponse` 模型
   - 定义 `ErrorCode` 枚举
   - 创建错误处理装饰器

2. **优化认证服务层**
   - 添加数据库事务
   - 完善边界情况处理
   - 添加结构化日志

3. **优化 API 层**
   - 统一错误响应格式
   - 添加详细日志
   - 完善 API 文档

4. **编写单元测试**
   - 核心逻辑测试
   - 边界情况测试
   - 事务回滚测试

#### 阶段2: 前端适配（1天）

1. **适配新的错误响应格式**
   - 更新 API 调用逻辑
   - 添加错误处理组件
   - 优化用户提示

2. **修复字段命名不匹配**
   - 调整字段转换逻辑
   - 更新 TypeScript 类型

3. **优化 Token刷新逻辑**
   - 实现队列机制
   - 添加重试逻辑

#### 阶段3: 测试与验证（1天）

1. **运行单元测试**
   ```bash
   pytest tests/ --cov=src --cov-report=html
   ```

2. **手动测试完整流程**
   - 注册流程
   - 登录流程
   - Token刷新
   - 边界情况

3. **性能测试**
   - 并发注册测试
   - Token刷新压力测试

#### 阶段4: 部署（30分钟）

1. **备份数据库**
   ```bash
   cp backend/job_copilot.db backend/job_copilot.db.backup
   ```

2. **部署后端**
   ```bash
   git pull
   pip install -r requirements.txt
   # 自动重启（假设使用 systemd）
   sudo systemctl restart job-copilot-backend
   ```

3. **部署前端**
   ```bash
   git pull
   npm install
   npm run build
   # 部署到 Web 服务器
   ```

4. **冒烟测试**
   - 访问首页
   - 测试注册
   - 测试登录

### 回滚策略

**触发条件**：

- 测试失败率 > 5%
- 严重错误（无法注册/登录）
- 性能下降 > 50%

**回滚步骤**：

1. **恢复数据库**（如果数据损坏）
   ```bash
   cp backend/job_copilot.db.backup backend/job_copilot.db
   ```

2. **回滚代码**
   ```bash
   git revert <commit-hash>
   git push
   ```

3. **重启服务**
   ```bash
   sudo systemctl restart job-copilot-backend
   # 重启 Web 服务器
   ```

4. **验证回滚成功**
   - 测试注册/登录功能
   - 检查日志无异常

## Open Questions

### Q1: 是否需要添加登录失败锁定机制？

**背景**：防止暴力破解攻击

**考虑**：
- 优点：提升安全性
- 缺点：增加复杂度，可能误伤正常用户

**建议**：
- 当前版本：仅记录失败日志
- 未来版本：添加 5 次失败后锁定 15 分钟

### Q2: 是否需要支持多个 Refresh Token？

**背景**：当前实现单设备登录（删除旧 Token）

**考虑**：
- 单设备：简化逻辑，安全性高
- 多设备：用户体验好，增加复杂度

**建议**：
- 当前版本：保持单设备登录
- 未来版本：添加设备管理功能

### Q3: 是否需要添加邮箱验证重发功能？

**背景**：验证码可能过期或丢失

**考虑**：
- 优点：提升用户体验
- 缺点：增加邮件发送成本

**建议**：
- 当前版本：支持重发（已有 rate-limit）
- 未来版本：添加冷却时间（60秒）

### Q4: 生产环境数据库选型？

**背景**：SQLite 不适合生产环境

**选项**：
- **PostgreSQL**：功能强大、性能好、社区支持（推荐）
- **MySQL**：兼容性好、应用广泛
- **MongoDB**：NoSQL、灵活（不适合关系型数据）

**建议**：
- 开发环境：保持 SQLite（简化开发）
- 生产环境：迁移到 PostgreSQL
- 迁移工具：Alembic（数据库迁移框架）
