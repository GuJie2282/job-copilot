# Structured Logging Capability

## Overview

结构化日志规范，确保关键操作和错误都有详细的日志记录，便于问题排查和系统监控。

## Requirements

### REQ-1: 日志级别定义

使用 Python 标准库 `logging` 模块，定义清晰的日志级别：

| 级别 | 使用场景 | 示例 |
|------|----------|------|
| DEBUG | 详细调试信息（开发环境） | 函数入参、中间变量、数据库查询 |
| INFO | 关键操作成功 | 用户注册成功、登录成功 |
| WARNING | 业务异常（非错误） | 验证码错误、密码错误 |
| ERROR | 系统错误 | 数据库异常、外部服务失败 |
| CRITICAL | 严重错误 | 服务不可用、数据损坏 |

### REQ-2: 日志格式规范

使用结构化 JSON 格式，包含标准字段：

```python
{
  "timestamp": "2025-01-01T10:00:00Z",    # ISO 8601 时间戳
  "level": "INFO",                        # 日志级别
  "event": "user_register_success",      # 事件名称
  "user_id": "123",                       # 用户 ID（如适用）
  "email": "test@example.com",           # 邮箱（脱敏）
  "ip": "127.0.0.1",                      # IP 地址
  "duration_ms": 150                      # 执行时间（毫秒）
}
```

### REQ-3: 关键路径日志

必须记录以下关键操作的日志：

#### 3.1 用户注册

```python
logger.info(
    "user_register_start",
    extra={
        "email": email,
        "ip": request.client.host
    }
)

# ... 注册逻辑

logger.info(
    "user_register_success",
    extra={
        "user_id": str(user.id),
        "email": user.email,
        "duration_ms": (end_time - start_time) * 1000
    }
)
```

#### 3.2 用户登录

```python
logger.info(
    "user_login_attempt",
    extra={
        "email": login_data.email,
        "ip": request.client.host
    }
)

# ... 登录逻辑

if login_success:
    logger.info(
        "user_login_success",
        extra={
            "user_id": str(user.id),
            "email": user.email,
            "ip": request.client.host
        }
    )
else:
    logger.warning(
        "user_login_failed",
        extra={
            "email": login_data.email,
            "reason": "invalid_password",
            "ip": request.client.host
        }
    )
```

#### 3.3 验证码发送

```python
logger.info(
    "verification_code_sent",
    extra={
        "email": email,
        "ip": request.client.host,
        "code": mask_code(code)  # 仅记录前2位，如 "12****"
    }
)
```

#### 3.4 Token刷新

```python
logger.info(
    "token_refresh_attempt",
    extra={
        "user_id": user_id,
        "ip": request.client.host
    }
)

# ... 刷新逻辑

logger.info(
    "token_refresh_success",
    extra={
        "user_id": user_id,
        "old_token": mask_token(refresh_token_str),  # 脱敏
        "new_token": mask_token(new_refresh_token)   # 脱敏
    }
)
```

### REQ-4: 敏感信息脱敏

以下敏感信息必须脱敏：

```python
def mask_email(email: str) -> str:
    """脱敏邮箱：test@example.com → te**@example.com"""
    if "@" not in email:
        return email
    username, domain = email.split("@", 1)
    return f"{username[:2]}**@{domain}"

def mask_phone(phone: str) -> str:
    """脱敏手机号：13812345678 → 138****5678"""
    if len(phone) < 7:
        return phone
    return f"{phone[:3]}****{phone[-4:]}"

def mask_token(token: str) -> str:
    """脱敏 Token：显示前8位和后4位"""
    if len(token) < 12:
        return "***"
    return f"{token[:8]}...{token[-4:]}"

def mask_code(code: str) -> str:
    """脱敏验证码：123456 → 12****"""
    if len(code) < 2:
        return "***"
    return f"{code[:2]}****"
```

**使用示例**：

```python
logger.info("user_login", email=mask_email(user.email))  # ✅ 正确
logger.info("user_login", email=user.email)              # ❌ 错误：泄露邮箱
logger.debug("token", token=mask_token(token))           # ✅ 正确
logger.debug("token", token=token)                       # ❌ 错误：泄露Token
```

### REQ-5: 日志配置

**开发环境配置**：

```python
# src/core/logging.py
import logging
import json

class JsonFormatter(logging.Formatter):
    """JSON 格式化器"""

    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "event": record.msg,
            "logger": record.name,
        }

        # 添加 extra 字段
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "email"):
            log_data["email"] = record.email
        # ... 更多字段

        return json.dumps(log_data, ensure_ascii=False)

# 配置日志
def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # 开发环境使用 DEBUG

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(JsonFormatter())

    logger.addHandler(console_handler)
```

**生产环境配置**：

```python
def setup_logging_production():
    """生产环境日志配置"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)  # 生产环境使用 INFO

    # 文件处理器（按日期轮转）
    from logging.handlers import TimedRotatingFileHandler

    file_handler = TimedRotatingFileHandler(
        "logs/job-copilot.log",
        when="midnight",
        backupCount=30  # 保留30天
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(JsonFormatter())

    logger.addHandler(file_handler)
```

### REQ-6: 错误日志增强

所有 ERROR 和 CRITICAL 级别的日志必须包含：

- 异常堆栈（`exc_info=True`）
- 请求上下文（用户 ID、IP、请求路径）
- 相关数据（如适用）

```python
try:
    # 危险操作
    result = risky_operation()
except Exception as e:
    logger.error(
        "operation_failed",
        extra={
            "user_id": user_id,
            "operation": "risky_operation",
            "error_type": type(e).__name__,
            "error_message": str(e)
        },
        exc_info=True  # 包含堆栈
    )
    raise
```

## Examples

### 示例1: 完整的注册流程日志

```python
def register_user(db: Session, register_data: RegisterRequest):
    start_time = time.time()

    logger.info(
        "user_register_start",
        extra={
            "email": mask_email(register_data.email),
            "name": register_data.name
        }
    )

    try:
        # 验证码验证
        logger.debug("verify_code_start", email=mask_email(register_data.email))
        verification_code = verify_code(db, register_data)
        logger.debug("verify_code_success", code=mask_code(verification_code.code))

        # 创建用户
        logger.debug("create_user_start", email=mask_email(register_data.email))
        user = create_user(db, register_data)
        logger.debug("create_user_success", user_id=str(user.id))

        # 生成 Token
        logger.debug("generate_token_start", user_id=str(user.id))
        tokens = generate_tokens(user)
        logger.debug("generate_token_success", user_id=str(user.id))

        duration_ms = (time.time() - start_time) * 1000

        logger.info(
            "user_register_success",
            extra={
                "user_id": str(user.id),
                "email": mask_email(user.email),
                "duration_ms": duration_ms
            }
        )

        return user, tokens

    except HTTPException as e:
        logger.warning(
            "user_register_failed",
            extra={
                "email": mask_email(register_data.email),
                "error_code": e.detail.get("code"),
                "error_message": e.detail.get("message")
            }
        )
        raise

    except Exception as e:
        logger.error(
            "user_register_error",
            extra={
                "email": mask_email(register_data.email),
                "error_type": type(e).__name__,
                "error_message": str(e)
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail={"code": "SYSTEM_INTERNAL_ERROR", "message": "系统错误"}
        )
```

### 示例2: 登录失败日志

```python
def login_user(db: Session, login_data: LoginRequest):
    logger.info(
        "user_login_attempt",
        extra={
            "email": mask_email(login_data.email),
            "ip": "..."  # 从 request 获取
        }
    )

    user = db.query(User).filter(User.email == login_data.email).first()

    if not user:
        logger.warning(
            "user_login_failed",
            extra={
                "email": mask_email(login_data.email),
                "reason": "user_not_found",
                "ip": "..."
            }
        )
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTH_INVALID_CREDENTIALS", "message": "邮箱或密码错误"}
        )

    if not verify_password(login_data.password, user.password_hash):
        logger.warning(
            "user_login_failed",
            extra={
                "user_id": str(user.id),
                "email": mask_email(user.email),
                "reason": "invalid_password",
                "ip": "..."
            }
        )
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTH_INVALID_CREDENTIALS", "message": "邮箱或密码错误"}
        )
```

### 示例3: 数据库错误日志

```python
try:
    db.add(new_user)
    db.commit()
except IntegrityError as e:
    logger.error(
        "database_integrity_error",
        extra={
            "operation": "create_user",
            "email": mask_email(register_data.email),
            "error_type": "IntegrityError",
            "error_message": str(e)
        },
        exc_info=True
    )
    raise HTTPException(
        status_code=500,
        detail={"code": "SYSTEM_DATABASE_ERROR", "message": "数据库错误"}
    )
```

## Implementation Notes

### 日志记录最佳实践

1. **结构化优先**：使用 JSON 格式，便于日志分析和查询
2. **上下文完整**：每个日志包含足够的上下文信息
3. **性能考虑**：使用异步日志（生产环境）
4. **日志轮转**：按日期/大小轮转，避免磁盘占满
5. **敏感信息保护**：始终脱敏敏感字段

### 日志分析

使用 ELK（Elasticsearch + Logstash + Kibana）或类似工具进行日志分析：

```bash
# 查询所有注册失败
curl -X GET "localhost:9200/logs/_search?q=event:user_register_failed"

# 查询特定用户的操作
curl -X GET "localhost:9200/logs/_search?q=user_id:123"

# 查询错误日志
curl -X GET "localhost:9200/logs/_search?q=level:ERROR"
```

### 监控和告警

- **ERROR 级别日志**：立即告警（邮件/短信）
- **WARNING 级别日志**：每小时汇总告警
- **慢事务日志**：超过1秒的事务记录并告警

## Testing

### 测试要求

1. **日志输出测试**：验证日志格式正确
2. **脱敏测试**：验证敏感信息被正确脱敏
3. **性能测试**：验证日志不影响业务性能

### 测试用例示例

```python
import logging
from io import StringIO

def test_log_format():
    """测试日志格式"""
    # 捕获日志输出
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setFormatter(JsonFormatter())

    logger.addHandler(handler)
    logger.info("test_event", extra={"user_id": "123"})

    # 验证 JSON 格式
    import json
    log_data = json.loads(log_stream.getvalue())
    assert log_data["event"] == "test_event"
    assert log_data["user_id"] == "123"

def test_email_masking():
    """测试邮箱脱敏"""
    assert mask_email("test@example.com") == "te**@example.com"
    assert mask_email("a@b.com") == "a**@b.com"

def test_token_masking():
    """测试 Token 脱敏"""
    long_token = "a" * 100
    masked = mask_token(long_token)
    assert len(masked) < len(long_token)
    assert "..." in masked
```
