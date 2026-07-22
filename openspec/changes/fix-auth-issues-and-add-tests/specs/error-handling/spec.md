# Error Handling Capability

## Overview

统一的错误处理规范，确保所有 API 端点返回结构化、用户友好的错误响应。

## Requirements

### REQ-1: 统一错误响应格式

所有 API 错误响应必须遵循统一的结构化格式：

```python
class ErrorResponse(BaseModel):
    code: str                      # 错误码（如 AUTH_EMAIL_EXISTS）
    message: str                   # 用户友好的中文消息
    details: Optional[Dict] = None # 详细信息（仅开发环境）
    action: Optional[str] = None   # 建议操作（如 "login"）
```

**验证标准**：
- 所有 HTTPException 必须使用此格式
- 错误码必须来自预定义的 ErrorCode 枚举
- 错误消息必须对用户友好、可操作

### REQ-2: 错误码体系

错误码采用模块化命名规范：`<DOMAIN>_<ERROR>_<DETAIL>`

**错误域（Domain）**：
- `AUTH_*`: 认证相关错误
- `CODE_*`: 验证码相关错误
- `TOKEN_*`: Token 相关错误
- `VALID_*`: 数据验证错误
- `SYSTEM_*`: 系统级错误

**必须实现的错误码**：

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

### REQ-3: 错误消息设计原则

**消息设计原则**：
1. **用户友好**：使用中文，避免技术术语
2. **可操作**：告诉用户具体问题和解决方法
3. **安全性**：不泄露系统内部信息
4. **一致性**：同类错误使用相同的消息模板

**错误消息示例**：

```python
ERROR_MESSAGES = {
    "AUTH_EMAIL_EXISTS": "该邮箱已被注册，请直接登录",
    "CODE_EXPIRED": "验证码已过期（5分钟有效期），请重新获取",
    "TOKEN_EXPIRED": "登录已过期，请重新登录",
    "VALID_PASSWORD_TOO_SHORT": "密码长度至少6位，请重新输入",
    # ... 更多错误消息
}
```

### REQ-4: HTTP 状态码使用规范

| 状态码 | 使用场景 | 示例 |
|--------|----------|------|
| 400 | 请求参数错误 | 验证码无效、邮箱格式错误 |
| 401 | 未认证 | Token过期、密码错误 |
| 403 | 禁止访问 | 账户禁用 |
| 404 | 资源不存在 | 用户不存在 |
| 429 | 请求过于频繁 | 验证码发送过于频繁 |
| 500 | 服务器内部错误 | 数据库异常 |

### REQ-5: 异常处理装饰器

创建统一的异常处理装饰器，自动转换异常为错误响应：

```python
def handle_errors(func):
    """统一异常处理装饰器"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except HTTPException:
            raise  # FastAPI HTTPException 已经处理
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail={"code": "VALID_ERROR", "message": str(e)}
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "code": "SYSTEM_INTERNAL_ERROR",
                    "message": "系统内部错误，请稍后重试"
                }
            )
    return wrapper
```

## Examples

### 示例1: 注册时的邮箱已存在错误

**请求**：
```json
POST /api/auth/register
{
  "name": "张三",
  "email": "existing@example.com",
  "password": "password123",
  "verification_code": "123456"
}
```

**响应**：
```json
HTTP 400 Bad Request
{
  "code": "AUTH_EMAIL_EXISTS",
  "message": "该邮箱已被注册，请直接登录",
  "action": "login"
}
```

### 示例2: 验证码过期错误

**请求**：
```json
POST /api/auth/register
{
  "name": "张三",
  "email": "test@example.com",
  "password": "password123",
  "verification_code": "123456"
}
```

**响应**：
```json
HTTP 400 Bad Request
{
  "code": "CODE_EXPIRED",
  "message": "验证码已过期（5分钟有效期），请重新获取",
  "action": "resend_code"
}
```

### 示例3: Token过期错误

**请求**：
```json
POST /api/protected-resource
Authorization: Bearer <expired-token>
```

**响应**：
```json
HTTP 401 Unauthorized
{
  "code": "TOKEN_EXPIRED",
  "message": "登录已过期，请重新登录",
  "action": "login"
}
```

### 示例4: 数据验证错误

**请求**：
```json
POST /api/auth/register
{
  "name": "张三",
  "email": "invalid-email",
  "password": "123",
  "verification_code": "123456"
}
```

**响应**：
```json
HTTP 400 Bad Request
{
  "code": "VALID_EMAIL_FORMAT",
  "message": "邮箱格式不正确，请输入有效的邮箱地址",
  "action": "fix_email"
}
```

## Implementation Notes

### 错误处理最佳实践

1. **早返回（Fail Fast）**：尽早验证输入，快速失败
2. **异常链（Exception Chaining）**：保留原始异常信息用于调试
3. **日志记录**：所有错误必须记录到日志（包含上下文）
4. **错误监控**：生产环境集成错误监控（如 Sentry）

### 环境差异化

```python
# 开发环境：显示详细错误信息
if DEBUG:
    error_response["details"] = {
        "traceback": traceback.format_exc(),
        "sql": str(e)
    }

# 生产环境：仅记录日志，不返回详细信息
logger.error(f"Error details: {e}", exc_info=True)
```

## Testing

### 测试要求

1. **单元测试**：每个错误码必须有对应的测试用例
2. **集成测试**：验证错误响应格式正确性
3. **端到端测试**：验证前端错误处理逻辑

### 测试用例示例

```python
def test_register_email_exists(client, db):
    """测试邮箱已存在的错误处理"""
    # 准备：创建已存在的用户
    create_user(db, email="test@example.com")

    # 执行：尝试注册相同邮箱
    response = client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "password123",
        "verification_code": "123456"
    })

    # 验证
    assert response.status_code == 400
    assert response.json()["code"] == "AUTH_EMAIL_EXISTS"
    assert "action" in response.json()
```
