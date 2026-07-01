# 用户认证能力规范

## ADDED Requirements

### Requirement: 用户可以通过邮箱和密码注册

系统 SHALL 允许新用户通过提供姓名、邮箱、密码和验证码来注册账户。

**注册验证规则：**
- 邮箱格式必须有效（符合 RFC 5322 标准）
- 密码长度至少 6 个字符
- 验证码必须是 6 位数字
- 验证码必须有效且未过期
- 验证码必须与发送到该邮箱的验证码匹配
- 邮箱尚未被注册

**安全要求：**
- 密码必须使用 bcrypt 算法哈希后存储（成本因子 12）
- 不得以明文形式存储密码
- 验证码一次性使用，使用后立即标记为已消耗

#### Scenario: 成功注册

- **GIVEN** 系统已启动并运行
- **WHEN** 用户提交注册请求，包含有效信息：
  - 姓名：`张三`
  - 邮箱：`zhangsan@example.com`
  - 密码：`password123`
  - 验证码：`123456`（已发送到该邮箱且未过期）
- **THEN** 系统创建用户账户
- **AND** 系统返回 HTTP 201 状态码
- **AND** 响应包含用户信息和 JWT Token：
  ```json
  {
    "code": 201,
    "message": "注册成功",
    "data": {
      "user": {
        "id": "uuid",
        "name": "张三",
        "email": "zhangsan@example.com",
        "createdAt": "2025-01-01T00:00:00Z"
      },
      "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "refreshToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    }
  }
  ```

#### Scenario: 邮箱已被注册

- **GIVEN** 系统中已存在邮箱为 `zhangsan@example.com` 的用户
- **WHEN** 用户尝试用相同邮箱注册
- **THEN** 系统返回 HTTP 400 错误
- **AND** 错误消息：`该邮箱已被注册`

#### Scenario: 验证码无效或已过期

- **GIVEN** 用户请求了验证码
- **WHEN** 用户提交注册请求，但验证码错误或已过期（超过 5 分钟）
- **THEN** 系统返回 HTTP 400 错误
- **AND** 错误消息：`验证码无效或已过期`

#### Scenario: 密码长度不足

- **GIVEN** 用户填写注册表单
- **WHEN** 用户提交密码少于 6 个字符的注册请求
- **THEN** 系统返回 HTTP 400 错误
- **AND** 错误消息：`密码长度至少为 6 个字符`

---

### Requirement: 用户可以通过邮箱和密码登录

系统 SHALL 允许已注册用户通过邮箱和密码进行身份验证。

**登录验证规则：**
- 邮箱必须在系统中存在
- 提供的密码必须与存储的哈希密码匹配
- 账户必须处于激活状态（未被禁用）

**Token 颁发：**
- 成功登录后，系统必须颁发 Access Token（有效期 15 分钟）
- 成功登录后，系统必须颁发 Refresh Token（有效期 7 天）
- Token 必须包含用户 ID 和邮箱
- Token 必须使用 HMAC SHA256 算法签名

#### Scenario: 成功登录

- **GIVEN** 系统中存在用户：
  - 邮箱：`zhangsan@example.com`
  - 密码：`password123`（已哈希存储）
- **WHEN** 用户提交登录请求：
  ```json
  {
    "email": "zhangsan@example.com",
    "password": "password123"
  }
  ```
- **THEN** 系统返回 HTTP 200 状态码
- **AND** 响应包含用户信息和 JWT Token：
  ```json
  {
    "code": 200,
    "message": "登录成功",
    "data": {
      "user": {
        "id": "uuid",
        "name": "张三",
        "email": "zhangsan@example.com"
      },
      "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "refreshToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    }
  }
  ```
- **AND** 系统记录用户的登录时间

#### Scenario: 邮箱不存在

- **GIVEN** 系统中不存在邮箱 `notexist@example.com`
- **WHEN** 用户尝试用该邮箱登录
- **THEN** 系统返回 HTTP 401 错误
- **AND** 错误消息：`邮箱或密码错误`（不透露邮箱是否存在）

#### Scenario: 密码错误

- **GIVEN** 系统中存在用户 `zhangsan@example.com`，密码为 `password123`
- **WHEN** 用户提交错误的密码（如 `wrongpassword`）
- **THEN** 系统返回 HTTP 401 错误
- **AND** 错误消息：`邮箱或密码错误`

---

### Requirement: 系统可以发送邮箱验证码

系统 SHALL 允许用户请求发送验证码到指定邮箱。

**验证码规则：**
- 验证码必须是 6 位数字（000000-999999）
- 验证码有效期为 5 分钟
- 验证码一次性使用，使用后立即失效

**限流要求：**
- 同一 IP 地址每分钟最多请求 5 次
- 同一邮箱每分钟最多请求 1 次
- 超过限流阈值时返回 HTTP 429 错误

**发送方式：**
- 开发环境：验证码打印到后端控制台
- 生产环境：验证码通过电子邮件发送

#### Scenario: 成功发送验证码（开发环境）

- **GIVEN** 系统运行在开发环境（`ENV=development`）
- **WHEN** 用户请求发送验证码到 `zhangsan@example.com`
- **THEN** 系统生成 6 位数字验证码
- **AND** 系统将验证码存储到数据库，标记为未使用
- **AND** 系统在控制台打印验证码：`📧 验证码: 123456`
- **AND** 系统返回 HTTP 200 状态码
- **AND** 响应消息：`验证码已发送`

#### Scenario: 邮箱请求过于频繁

- **GIVEN** 邮箱 `zhangsan@example.com` 在 1 分钟内已请求过验证码
- **WHEN** 用户在 1 分钟内再次请求发送验证码到该邮箱
- **THEN** 系统返回 HTTP 429 错误
- **AND** 错误消息：`请求过于频繁，请稍后再试`
- **AND** 系统不发送新的验证码

#### Scenario: IP 地址请求过于频繁

- **GIVEN** IP 地址 `192.168.1.100` 在 1 分钟内已请求 5 次验证码
- **WHEN** 该 IP 再次请求发送验证码（任意邮箱）
- **THEN** 系统返回 HTTP 429 错误
- **AND** 错误消息：`请求过于频繁，请稍后再试`

#### Scenario: 验证码有效期管理

- **GIVEN** 系统中存在过期验证码（创建时间超过 5 分钟）
- **WHEN** 用户尝试使用该验证码注册
- **THEN** 系统返回 HTTP 400 错误
- **AND** 错误消息：`验证码已过期`
- **AND** 系统标记该验证码为已使用（防止重放）

---

### Requirement: 用户可以退出登录

系统 SHALL 允许已登录用户退出登录。

**退出登录行为：**
- 删除服务器的 Refresh Token
- 前端清除本地存储的 Token
- 后续请求携带旧 Token 将返回 401 错误

#### Scenario: 成功退出登录

- **GIVEN** 用户已登录，持有有效的 Access Token 和 Refresh Token
- **WHEN** 用户调用退出登录 API
  - Header：`Authorization: Bearer {access_token}`
- **THEN** 系统删除该用户的 Refresh Token
- **AND** 系统返回 HTTP 200 状态码
- **AND** 响应消息：`退出登录成功`

#### Scenario: Token 已失效时退出登录

- **GIVEN** 用户的 Access Token 已过期
- **WHEN** 用户调用退出登录 API
- **THEN** 系统返回 HTTP 401 错误
- **AND** 前端直接清除本地 Token（无需调用 API）

---

### Requirement: 系统必须保护 API 端点

系统 SHALL 对需要身份验证的 API 端点进行保护。

**保护机制：**
- 请求必须包含有效的 Authorization 头：`Bearer {access_token}`
- Token 无效或过期时返回 HTTP 401 错误
- Token 格式错误时返回 HTTP 401 错误

**公开端点（无需认证）：**
- `POST /auth/login`
- `POST /auth/register`
- `POST /auth/send-code`

**受保护端点（需要认证）：**
- `POST /auth/logout`
- `POST /auth/refresh`
- 其他业务 API（如用户资料、JD 匹配等）

#### Scenario: 携带有效 Token 访问受保护端点

- **GIVEN** 用户持有有效的 Access Token
- **WHEN** 用户请求受保护端点（如 `GET /api/users/profile`）
  - Header：`Authorization: Bearer {valid_token}`
- **THEN** 系统验证 Token 成功
- **AND** 系统返回请求的资源数据
- **AND** 返回 HTTP 200 状态码

#### Scenario: 未携带 Token 访问受保护端点

- **GIVEN** 用户未登录，无 Token
- **WHEN** 用户请求受保护端点（如 `GET /api/users/profile`）
- **THEN** 系统返回 HTTP 401 错误
- **AND** 错误消息：`未授权，请先登录`

#### Scenario: 携带过期 Token 访问受保护端点

- **GIVEN** 用户持有已过期的 Access Token
- **WHEN** 用户请求受保护端点，携带过期 Token
- **THEN** 系统返回 HTTP 401 错误
- **AND** 错误消息：`Token 已过期`
- **AND** 前端应尝试刷新 Token 或跳转登录页

---

### Requirement: 系统必须对注册登录输入进行验证

系统 SHALL 验证所有注册和登录请求的输入数据。

**验证规则：**
- 邮箱必须符合 RFC 5322 标准（正则表达式验证）
- 密码长度必须在 6-100 个字符之间
- 姓名长度必须在 2-50 个字符之间
- 手机号（可选）必须符合 E.164 格式（如 `+8613800138000`）

#### Scenario: 邮箱格式无效

- **WHEN** 用户提交注册请求，邮箱为 `invalid-email`
- **THEN** 系统返回 HTTP 400 错误
- **AND** 错误消息：`邮箱格式无效`

#### Scenario: 密码过长

- **WHEN** 用户提交注册请求，密码超过 100 个字符
- **THEN** 系统返回 HTTP 400 错误
- **AND** 错误消息：`密码长度不能超过 100 个字符`

#### Scenario: 姓名过短

- **WHEN** 用户提交注册请求，姓名为空或仅 1 个字符
- **THEN** 系统返回 HTTP 400 错误
- **AND** 错误消息：`姓名长度至少为 2 个字符`
