# Token 刷新能力规范

## ADDED Requirements

### Requirement: 系统支持 Refresh Token 机制

系统 SHALL 实现 Refresh Token 机制，允许用户在 Access Token 过期后获取新的 Access Token，无需重新登录。

**Token 类型：**
- **Access Token**：短期有效（15 分钟），用于 API 访问
- **Refresh Token**：长期有效（7 天），用于刷新 Access Token

**Refresh Token 规则：**
- Refresh Token 必须是有效的 JWT Token
- Refresh Token 必须存储在数据库中
- Refresh Token 必须与用户 ID 关联
- 每个 Refresh Token 只能使用一次（刷新后生成新的 Refresh Token）
- Refresh Token 过期后必须从数据库删除

#### Scenario: 成功刷新 Token

- **GIVEN** 用户已登录，持有有效的 Refresh Token
- **AND** 用户的 Access Token 已过期（或即将过期）
- **WHEN** 用户请求刷新 Token：
  ```json
  POST /auth/refresh
  {
    "refreshToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
  ```
- **THEN** 系统验证 Refresh Token 有效性
- **AND** 系统生成新的 Access Token（有效期 15 分钟）
- **AND** 系统生成新的 Refresh Token（有效期 7 天）
- **AND** 系统将旧的 Refresh Token 标记为已使用
- **AND** 系统返回 HTTP 200 状态码
- **AND** 响应包含新的 Token：
  ```json
  {
    "code": 200,
    "message": "Token 刷新成功",
    "data": {
      "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "refreshToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    }
  }
  ```

#### Scenario: Refresh Token 无效

- **GIVEN** 用户持有无效的 Refresh Token（如伪造、已被删除）
- **WHEN** 用户请求刷新 Token
- **THEN** 系统返回 HTTP 401 错误
- **AND** 错误消息：`Refresh Token 无效或已过期`

#### Scenario: Refresh Token 已过期

- **GIVEN** 用户持有超过 7 天有效期的 Refresh Token
- **WHEN** 用户请求刷新 Token
- **THEN** 系统返回 HTTP 401 错误
- **AND** 错误消息：`Refresh Token 无效或已过期`
- **AND** 系统从数据库删除该过期的 Refresh Token

---

### Requirement: 前端必须在 401 错误时自动刷新 Token

系统（前端）SHALL 在收到 HTTP 401 错误时，自动尝试刷新 Token，而不是立即跳转登录页。

**刷新流程：**
1. Axios 拦截器捕获 HTTP 401 错误
2. 检查是否有有效的 Refresh Token
3. 调用 `/auth/refresh` 端点
4. 获取新的 Access Token
5. 重试原始请求
6. 如果刷新失败，清除所有 Token 并跳转登录页

**防重试机制：**
- 使用 `_isRetry` 标记避免死循环
- 如果刷新请求本身返回 401，不再次刷新

#### Scenario: Access Token 过期，自动刷新成功

- **GIVEN** 用户已登录，持有有效的 Access Token 和 Refresh Token
- **AND** Access Token 已过期（如超过 15 分钟）
- **WHEN** 用户请求受保护端点（如 `GET /api/users/profile`）
- **THEN** Axios 拦截器捕获 HTTP 401 错误
- **AND** 拦截器自动调用 `/auth/refresh` 端点
- **AND** 系统返回新的 Access Token
- **AND** 拦截器将新 Token 存储到 localStorage
- **AND** 拦截器重试原始请求（`GET /api/users/profile`）
- **AND** 用户无感知，请求成功返回数据

#### Scenario: Access Token 过期，Refresh Token 也过期

- **GIVEN** 用户已登录，但 Access Token 和 Refresh Token 都已过期
- **WHEN** 用户请求受保护端点
- **THEN** Axios 拦截器捕获 HTTP 401 错误
- **AND** 拦截器尝试刷新 Token
- **AND** `/auth/refresh` 返回 HTTP 401 错误（Refresh Token 无效）
- **AND** 拦截器清除 localStorage 中的所有 Token
- **AND** 拦截器跳转到登录页（`/login`）

#### Scenario: 刷新请求本身返回 401

- **GIVEN** 用户的 Access Token 已过期
- **AND** 用户的 Refresh Token 无效或过期
- **WHEN** Axios 拦截器尝试刷新 Token
- **AND** `/auth/refresh` 返回 HTTP 401 错误
- **THEN** 拦截器不再次刷新（避免死循环）
- **AND** 拦截器清除所有 Token
- **AND** 拦截器跳转到登录页

---

### Requirement: 系统必须支持并发请求的 Token 刷新

系统 SHALL 正确处理多个并发请求同时收到 401 错误的情况。

**并发问题：**
- 如果多个请求同时过期，可能触发多次刷新请求
- 多次刷新会导致 Token 不一致或浪费资源

**解决方案：**
- 使用 Token 刷新锁（或队列）
- 仅允许一个刷新请求进行
- 其他请求等待刷新完成

#### Scenario: 多个并发请求同时过期

- **GIVEN** 用户已登录，Access Token 即将过期
- **WHEN** 前端同时发起 3 个 API 请求：
  - Request A：`GET /api/users/profile`
  - Request B：`GET /api/jobs/list`
  - Request C：`GET /api/resume/status`
- **AND** 所有 3 个请求都返回 HTTP 401 错误
- **THEN** Axios 拦截器仅调用一次 `/auth/refresh`
- **AND** 其他 2 个请求等待刷新完成
- **AND** 刷新完成后，所有 3 个请求使用新的 Token 重试
- **AND** 所有请求成功返回数据

---

### Requirement: 前端必须正确存储和管理 Refresh Token

系统（前端）SHALL 正确存储 Refresh Token，并在必要时清除。

**存储要求：**
- Refresh Token 存储在 localStorage（当前实现）
- 键名：`refreshToken`
- 与 Access Token（`token`）分开存储

**清除要求：**
- 退出登录时清除
- Refresh Token 刷新失败时清除
- Refresh Token 过期时清除
- 用户手动退出时清除

#### Scenario: 登录成功后存储 Refresh Token

- **GIVEN** 用户成功登录
- **WHEN** 后端返回 Access Token 和 Refresh Token
- **THEN** 前端将 Access Token 存储到 `localStorage.token`
- **AND** 前端将 Refresh Token 存储到 `localStorage.refreshToken`

#### Scenario: 退出登录时清除 Refresh Token

- **GIVEN** 用户已登录
- **WHEN** 用户点击"退出登录"按钮
- **THEN** 前端调用 `POST /auth/logout`
- **AND** 前端清除 `localStorage.token`
- **AND** 前端清除 `localStorage.refreshToken`
- **AND** 前端跳转到登录页

#### Scenario: Token 刷新失败时清除所有 Token

- **GIVEN** 用户的 Access Token 已过期
- **WHEN** Token 刷新失败（Refresh Token 无效）
- **THEN** 前端清除 `localStorage.token`
- **AND** 前端清除 `localStorage.refreshToken`
- **AND** 前端跳转到登录页

---

### Requirement: 后端必须验证 Refresh Token 的完整性

系统（后端）SHALL 验证 Refresh Token 的完整性和有效性。

**验证项目：**
- JWT 签名验证（防篡改）
- Token 未过期（检查 `exp` 声明）
- Token 存在于数据库（防伪造）
- Token 未被标记为已使用（防重放）
- Token 关联的用户存在且激活

#### Scenario: 验证 Refresh Token 签名

- **GIVEN** 系统收到刷新 Token 请求
- **WHEN** Refresh Token 的签名被篡改
- **THEN** 系统返回 HTTP 401 错误
- **AND** 错误消息：`Refresh Token 无效`

#### Scenario: 验证 Refresh Token 存在性

- **GIVEN** 系统收到刷新 Token 请求
- **WHEN** Refresh Token 有效，但不存在于数据库中
- **THEN** 系统返回 HTTP 401 错误
- **AND** 错误消息：`Refresh Token 无效`
- **AND** 系统记录安全警告（可能的伪造尝试）

#### Scenario: 验证 Refresh Token 重放攻击

- **GIVEN** 系统收到刷新 Token 请求
- **WHEN** Refresh Token 已被使用过（数据库标记为已使用）
- **THEN** 系统返回 HTTP 401 错误
- **AND** 错误消息：`Refresh Token 已被使用`
- **AND** 系统记录安全警告（可能的重放攻击）

---

### Requirement: 系统必须在刷新 Token 时轮换 Refresh Token

系统 SHALL 在每次刷新 Token 时生成新的 Refresh Token，并使旧的 Refresh Token 失效。

**轮换机制：**
- 刷新成功后，生成新的 Refresh Token
- 将旧的 Refresh Token 标记为已使用
- 将新的 Refresh Token 存储到数据库
- 返回新的 Access Token 和 Refresh Token

**安全原因：**
- 防止 Refresh Token 被长期滥用
- 如果 Refresh Token 泄露，缩短其有效时间

#### Scenario: 刷新 Token 后旧 Token 失效

- **GIVEN** 用户持有 Refresh Token A
- **WHEN** 用户使用 Refresh Token A 刷新 Token
- **THEN** 系统生成新的 Refresh Token B
- **AND** 系统标记 Refresh Token A 为已使用
- **AND** 系统返回新的 Refresh Token B
- **AND** 如果用户再次尝试使用 Refresh Token A，系统返回 HTTP 401 错误

#### Scenario: 连续刷新 Token

- **GIVEN** 用户持有 Refresh Token A
- **WHEN** 用户第一次刷新 Token
- **THEN** 系统返回 Refresh Token B
- **AND** Refresh Token A 失效
- **WHEN** 用户使用 Refresh Token B 第二次刷新
- **THEN** 系统返回 Refresh Token C
- **AND** Refresh Token B 失效

---

### Requirement: 前端必须在刷新请求中携带 Refresh Token

系统（前端）SHALL 在刷新 Token 请求中正确携带 Refresh Token。

**请求格式：**
- 端点：`POST /auth/refresh`
- 请求体：`{ "refreshToken": "..." }`
- 不得在 Authorization 头中携带 Access Token（因为已过期）

#### Scenario: 刷新请求格式正确

- **GIVEN** 用户持有有效的 Refresh Token
- **WHEN** Access Token 过期，前端发起刷新请求
- **THEN** 前端发送 POST 请求到 `/auth/refresh`
- **AND** 请求体包含：
  ```json
  {
    "refreshToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
  ```
- **AND** 请求不包含 Authorization 头（或包含过期的 Access Token）

#### Scenario: 刷新请求缺少 Refresh Token

- **GIVEN** 前端发起刷新请求
- **WHEN** 请求体中缺少 `refreshToken` 字段
- **THEN** 系统返回 HTTP 400 错误
- **AND** 错误消息：`缺少 Refresh Token`

---

### Requirement: 系统必须支持单设备登录（踢出其他设备）

系统 SHALL 在用户登录时，删除该用户的所有旧 Refresh Token，确保单设备登录。

**单设备逻辑：**
- 用户登录成功后，删除数据库中该用户的所有 Refresh Token
- 仅保留当前登录生成的 Refresh Token
- 旧设备的 Token 刷新将失败，强制重新登录

#### Scenario: 新登录踢出旧设备

- **GIVEN** 用户在设备 A 登录，持有 Refresh Token A
- **WHEN** 用户在设备 B 重新登录
- **THEN** 系统删除 Refresh Token A
- **AND** 系统为设备 B 生成新的 Refresh Token B
- **AND** 当设备 A 尝试刷新 Token 时，系统返回 HTTP 401 错误
- **AND** 错误消息：`Refresh Token 无效`
- **AND** 设备 A 被迫重新登录

#### Scenario: 用户主动踢出其他设备

- **GIVEN** 用户在多个设备登录
- **WHEN** 用户在当前设备点击"踢出其他设备"（未来功能）
- **THEN** 系统删除该用户的所有旧 Refresh Token
- **AND** 系统为当前设备生成新的 Refresh Token
- **AND** 其他设备的刷新请求失败
