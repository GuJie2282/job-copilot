# User Registration Capability (DELTA)

## Overview

此文档定义了对用户注册能力的 REQUIREMENTS 变更。这是对现有 `user-registration` 规范的增量更新。

##变更类型

**DELTA SPEC** - 此文档修改现有能力的要求

## New Requirements

### REQ-REG-001: 事务原子性

用户注册必须使用数据库事务确保数据一致性：

**要求**：
1. 验证码验证和标记必须在一个事务内完成
2. 用户创建必须在独立事务内完成
3. Token生成失败不应影响用户创建
4. 任何失败场景必须回滚相关事务

**验证标准**：
- 所有数据库操作使用 `with db.begin()` 上下文管理器
- 事务失败时数据自动回滚
- 验证码标记和用户创建不在同一事务（避免Token生成失败影响验证码）

### REQ-REG-002: 边界情况处理

注册流程必须处理以下边界情况：

| 场景 | 错误码 | 错误消息 | Action |
|------|--------|----------|--------|
| 邮箱已注册 | AUTH_EMAIL_EXISTS | 该邮箱已被注册，请直接登录 | login |
| 验证码无效 | CODE_INVALID | 验证码错误，请检查或重新获取 | resend_code |
| 验证码过期 | CODE_EXPIRED | 验证码已过期（5分钟有效期），请重新获取 | resend_code |
| 验证码已使用 | CODE_ALREADY_USED | 验证码已使用，请重新获取 | resend_code |
| 密码过长 | VALID_PASSWORD_TOO_LONG | 密码过长，请使用72字符以内的密码 | fix_password |
| 邮箱格式错误 | VALID_EMAIL_FORMAT | 邮箱格式不正确，请输入有效的邮箱地址 | fix_email |
| 手机号格式错误 | VALID_PHONE_FORMAT | 手机号格式不正确，请输入有效的手机号 | fix_phone |

**验证标准**：
- 每个边界情况有专门的测试用例
- 错误响应包含 code、message、action 字段
- 前端根据 action 字段引导用户操作

### REQ-REG-003: 友好错误消息

注册失败时必须提供用户友好的错误消息：

**要求**：
- 使用中文，避免技术术语
- 明确指出问题所在
- 提供解决方法或建议操作
- 不泄露系统内部信息

**示例**：

```json
// ❌ 错误：不友好的错误消息
{
  "detail": "验证码无效"
}

// ✅ 正确：友好的错误消息
{
  "code": "CODE_EXPIRED",
  "message": "验证码已过期（5分钟有效期），请重新获取",
  "action": "resend_code"
}
```

### REQ-REG-004: 数据验证增强

注册请求必须验证以下字段：

| 字段 | 验证规则 | 错误码 |
|------|----------|--------|
| email | 有效邮箱格式、未注册 | VALID_EMAIL_FORMAT / AUTH_EMAIL_EXISTS |
| password | 最小6位、最大72字节 | VALID_PASSWORD_TOO_SHORT / VALID_PASSWORD_TOO_LONG |
| phone | 有效手机号格式（可选） | VALID_PHONE_FORMAT |
| verification_code | 6位数字、有效、未使用、未过期 | CODE_* |

**验证顺序**：
1. 字段格式验证（邮箱、手机号、密码长度）
2. 邮箱唯一性验证
3. 验证码有效性验证
4. 创建用户

### REQ-REG-005: 结构化日志

注册流程必须记录以下日志：

```python
# 开始
logger.info("user_register_start", extra={"email": mask_email(email)})

# 关键步骤
logger.debug("verify_code_success", email=mask_email(email))
logger.debug("create_user_success", user_id=str(user.id))

# 成功
logger.info("user_register_success", extra={
    "user_id": str(user.id),
    "email": mask_email(user.email),
    "duration_ms": duration_ms
})

# 失败
logger.warning("user_register_failed", extra={
    "email": mask_email(email),
    "error_code": error_code,
    "error_message": error_message
})
```

## Modified Requirements

### 修改：REQ-REG-OLD-001（原始注册流程）

**原始要求**：
- 注册流程包含验证码验证和用户创建

**新要求**：
- 注册流程划分为3个独立阶段：
  1. 验证码事务（验证 + 标记）
  2. 用户创建事务
  3. Token生成（非事务）

**变更原因**：
事务边界不清晰导致数据一致性风险

### 修改：REQ-REG-OLD-002（错误处理）

**原始要求**：
- 返回 HTTP 错误码和简单消息

**新要求**：
- 返回结构化错误响应（code、message、action）

**变更原因**：
用户体验差，前端无法智能处理错误

## Implementation Notes

### 注册流程伪代码

```python
def register_user(db: Session, register_data: RegisterRequest):
    start_time = time.time()

    logger.info("user_register_start", extra={"email": mask_email(register_data.email)})

    try:
        # 阶段1: 验证码事务
        with db.begin():
            code = verify_and_consume_code(db, register_data)
            logger.debug("code_verified", code=mask_code(code.code))

        # 阶段2: 用户创建事务
        with db.begin():
            check_email_exists(db, register_data.email)
            user = create_user(db, register_data)
            logger.debug("user_created", user_id=str(user.id))

        # 阶段3: Token生成（非事务）
        tokens = generate_tokens(user)
        store_refresh_token(db, user.id, tokens.refresh_token)

        duration_ms = (time.time() - start_time) * 1000
        logger.info("user_register_success", extra={
            "user_id": str(user.id),
            "email": mask_email(user.email),
            "duration_ms": duration_ms
        })

        return user, tokens

    except HTTPException as e:
        logger.warning("user_register_failed", extra={
            "email": mask_email(register_data.email),
            "error_code": e.detail["code"]
        })
        raise

    except Exception as e:
        logger.error("user_register_error", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"code": "SYSTEM_INTERNAL_ERROR", "message": "系统错误"}
        )
```

### 测试矩阵

| 测试场景 | 验证点 | 期望结果 |
|----------|--------|----------|
| 正常注册 | 事务完整性 | 用户创建成功、验证码已使用、Token有效 |
| 邮箱已存在 | 边界处理 | 返回 AUTH_EMAIL_EXISTS，无数据库变更 |
| 验证码过期 | 边界处理 | 返回 CODE_EXPIRED，无数据库变更 |
| 验证码已使用 | 边界处理 | 返回 CODE_ALREADY_USED，无数据库变更 |
| 密码过长 | 数据验证 | 返回 VALID_PASSWORD_TOO_LONG |
| 用户创建失败 | 事务回滚 | 验证码已使用、用户不存在、可重试 |
| Token生成失败 | 部分成功 | 用户创建成功、返回系统错误、可重新登录 |

## Migration Notes

### 对现有代码的影响

**需要修改的文件**：
1. `backend/src/services/auth_service.py` - 添加事务管理
2. `backend/src/api/auth.py` - 更新错误响应格式
3. `backend/src/schemas/auth.py` - 添加验证规则

**不需要修改**：
- 数据库模型（无结构变更）
- API 端点路径（保持兼容）

### 前端适配

**需要修改的文件**：
1. `web/src/api/auth.ts` - 适配新的错误响应格式
2. `web/src/views/Register.vue` - 显示友好错误消息

**错误处理示例**：

```typescript
// 注册失败处理
try {
  await authApi.register(registerData);
} catch (error) {
  const errorData = error.response.data;

  // 根据 action 字段自动处理
  switch (errorData.action) {
    case 'login':
      showLoginModal();  // 自动显示登录对话框
      break;
    case 'resend_code':
      highlightResendButton();  // 高亮"重新发送"按钮
      break;
    default:
      showErrorMessage(errorData.message);  // 显示错误消息
  }
}
```

## Testing

### 新增测试用例

```python
# tests/unit/test_auth_service.py
class TestRegisterUser:
    def test_register_success(self, test_db):
        """✅ 正常注册成功"""
        pass

    def test_register_email_exists(self, test_db):
        """✅ 邮箱已存在"""
        pass

    def test_register_code_invalid(self, test_db):
        """✅ 验证码无效"""
        pass

    def test_register_code_expired(self, test_db):
        """✅ 验证码过期"""
        pass

    def test_register_code_used(self, test_db):
        """✅ 验证码已使用"""
        pass

    def test_register_password_too_long(self, test_db):
        """✅ 密码过长"""
        pass

    def test_register_transaction_rollback(self, test_db):
        """✅ 事务回滚（用户创建失败）"""
        pass
```
