# User Login Capability (DELTA)

## Overview

此文档定义了对用户登录能力的 REQUIREMENTS 变更。这是对现有 `user-login` 规范的增量更新。

## 变更类型

**DELTA SPEC** - 此文档修改现有能力的要求

## New Requirements

### REQ-LOGIN-001: 密码错误提示优化

登录失败时必须提供区分化的错误提示（仅日志记录，不泄露给用户）：

**要求**：
1. 用户不存在：记录 "user_not_found"
2. 密码错误：记录 "invalid_password"
3. 账户禁用：返回明确错误 "账户已被禁用"
4. 用户端统一显示 "邮箱或密码错误"（安全考虑）

**日志记录**：

```python
if not user:
    logger.warning(
        "user_login_failed",
        extra={
            "email": mask_email(login_data.email),
            "reason": "user_not_found",
            "ip": request.client.host
        }
    )
    raise HTTPException(
        status_code=401,
        detail={
            "code": "AUTH_INVALID_CREDENTIALS",
            "message": "邮箱或密码错误"  # 不区分用户不存在和密码错误
        }
    )

if not verify_password(login_data.password, user.password_hash):
    logger.warning(
        "user_login_failed",
        extra={
            "user_id": str(user.id),
            "email": mask_email(user.email),
            "reason": "invalid_password",
            "ip": request.client.host
        }
    )
    raise HTTPException(
        status_code=401,
        detail={
            "code": "AUTH_INVALID_CREDENTIALS",
            "message": "邮箱或密码错误"
        }
    )
```

### REQ-LOGIN-002: 账户禁用状态处理

登录流程必须检查账户激活状态：

**要求**：
1. 账户禁用时返回 403 状态码
2. 错误码：`AUTH_ACCOUNT_DISABLED`
3. 错误消息：明确告知账户被禁用
4. 记录登录尝试日志

**示例**：

```json
HTTP 403 Forbidden
{
  "code": "AUTH_ACCOUNT_DISABLED",
  "message": "账户已被禁用，请联系管理员",
  "action": "contact_admin"
}
```

### REQ-LOGIN-003: 事务原子性

登录流程必须在单个事务内完成以下操作：

**要求**：
1. 用户查询和密码验证
2. 删除所有旧 Refresh Token（单设备登录）
3. 创建新 Refresh Token
4. 更新最后登录时间

**事务边界**：

```python
def login_user(db: Session, login_data: LoginRequest):
    """用户登录 - 单事务完成"""
    with db.begin():
        # 1. 查询用户
        user = db.query(User).filter(User.email == login_data.email).first()
        if not user:
            raise HTTPException(...)

        # 2. 验证密码
        if not verify_password(login_data.password, user.password_hash):
            raise HTTPException(...)

        # 3. 检查账户状态
        if not user.is_active:
            raise HTTPException(status_code=403, detail={
                "code": "AUTH_ACCOUNT_DISABLED",
                "message": "账户已被禁用"
            })

        # 4. 删除旧 Token
        db.query(RefreshToken).filter(
            RefreshToken.user_id == str(user.id)
        ).delete()

        # 5. 创建新 Token
        refresh_token_str = create_refresh_token(data={"user_id": str(user.id)})
        refresh_token_obj = RefreshToken(
            user_id=str(user.id),
            token=refresh_token_str,
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        db.add(refresh_token_obj)

        # 6. 更新登录时间
        user.last_login = datetime.utcnow()

    # 非事务操作：生成 Access Token
    access_token = create_access_token(data={
        "user_id": str(user.id),
        "email": user.email
    })

    return user, access_token, refresh_token_str
```

### REQ-LOGIN-004: 结构化日志

登录流程必须记录详细日志：

```python
# 登录尝试
logger.info(
    "user_login_attempt",
    extra={
        "email": mask_email(login_data.email),
        "ip": request.client.host
    }
)

# 登录成功
logger.info(
    "user_login_success",
    extra={
        "user_id": str(user.id),
        "email": mask_email(user.email),
        "ip": request.client.host,
        "duration_ms": duration_ms
    }
)

# 登录失败
logger.warning(
    "user_login_failed",
    extra={
        "email": mask_email(login_data.email),
        "reason": "invalid_password",  # 或 user_not_found
        "ip": request.client.host
    }
)
```

### REQ-LOGIN-005: 登录失败次数限制（未来扩展）

**当前版本**：仅记录失败日志

**未来版本**（REQ-LOGIN-005-FUTURE）：
- 同一IP 5分钟内失败5次，锁定15分钟
- 同一邮箱 1小时内失败10次，锁定1小时
- 管理员可手动解锁

**实现预留**：

```python
# 未来实现
def check_login_attempts(db: Session, email: str, ip: str):
    """检查登录失败次数"""
    recent_failures = db.query(LoginAttempt).filter(
        LoginAttempt.email == email,
        LoginAttempt.created_at > datetime.utcnow() - timedelta(hours=1)
    ).count()

    if recent_failures >= 10:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "AUTH_TOO_MANY_ATTEMPTS",
                "message": "登录尝试次数过多，请1小时后再试",
                "action": "wait"
            }
        )
```

## Modified Requirements

### 修改：REQ-LOGIN-OLD-001（原始登录流程）

**原始要求**：
- 登录流程包含用户查询、密码验证、Token生成

**新要求**：
- 登录流程在单个事务内完成（查询、验证、Token存储、时间更新）
- 区分失败原因（日志记录）
- 检查账户激活状态

**变更原因**：
- 数据一致性问题（Token删除和创建不在同一事务）
- 安全性问题（不区分失败原因，无法监控攻击）
- 用户体验问题（账户禁用无明确提示）

### 修改：REQ-LOGIN-OLD-002（错误处理）

**原始要求**：
- 返回 401 错误和简单消息

**新要求**：
- 账户禁用返回 403 错误
- 结构化错误响应（code、message、action）
- 区分失败原因（仅日志）

**变更原因**：
- 用户体验差（账户禁用无明确提示）
- 安全性不足（无法监控暴力破解）

## Implementation Notes

### 登录流程伪代码

```python
def login_user(db: Session, login_data: LoginRequest, request: Request):
    start_time = time.time()

    logger.info("user_login_attempt", extra={
        "email": mask_email(login_data.email),
        "ip": request.client.host
    })

    try:
        # 事务：用户认证 + Token管理
        with db.begin():
            # 1. 查询用户
            user = db.query(User).filter(User.email == login_data.email).first()
            if not user:
                logger.warning("user_login_failed", extra={
                    "email": mask_email(login_data.email),
                    "reason": "user_not_found",
                    "ip": request.client.host
                })
                raise HTTPException(
                    status_code=401,
                    detail={
                        "code": "AUTH_INVALID_CREDENTIALS",
                        "message": "邮箱或密码错误"
                    }
                )

            # 2. 验证密码
            if not verify_password(login_data.password, user.password_hash):
                logger.warning("user_login_failed", extra={
                    "user_id": str(user.id),
                    "email": mask_email(user.email),
                    "reason": "invalid_password",
                    "ip": request.client.host
                })
                raise HTTPException(
                    status_code=401,
                    detail={
                        "code": "AUTH_INVALID_CREDENTIALS",
                        "message": "邮箱或密码错误"
                    }
                )

            # 3. 检查账户状态
            if not user.is_active:
                logger.warning("user_login_disabled", extra={
                    "user_id": str(user.id),
                    "email": mask_email(user.email),
                    "ip": request.client.host
                })
                raise HTTPException(
                    status_code=403,
                    detail={
                        "code": "AUTH_ACCOUNT_DISABLED",
                        "message": "账户已被禁用，请联系管理员",
                        "action": "contact_admin"
                    }
                )

            # 4. 删除旧 Token
            db.query(RefreshToken).filter(
                RefreshToken.user_id == str(user.id)
            ).delete()

            # 5. 创建新 Refresh Token
            refresh_token_str = create_refresh_token(data={"user_id": str(user.id)})
            refresh_token_obj = RefreshToken(
                user_id=str(user.id),
                token=refresh_token_str,
                expires_at=datetime.utcnow() + timedelta(days=7)
            )
            db.add(refresh_token_obj)

            # 6. 更新登录时间
            user.last_login = datetime.utcnow()

        # 非事务：生成 Access Token
        access_token = create_access_token(data={
            "user_id": str(user.id),
            "email": user.email
        })

        duration_ms = (time.time() - start_time) * 1000

        logger.info("user_login_success", extra={
            "user_id": str(user.id),
            "email": mask_email(user.email),
            "ip": request.client.host,
            "duration_ms": duration_ms
        })

        return user, access_token, refresh_token_str

    except HTTPException:
        raise
    except Exception as e:
        logger.error("user_login_error", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"code": "SYSTEM_INTERNAL_ERROR", "message": "系统错误"}
        )
```

### 测试矩阵

| 测试场景 | 验证点 | 期望结果 |
|----------|--------|----------|
| 正常登录 | 事务完整性 | Token更新、登录时间更新 |
| 用户不存在 | 错误处理 | 返回401、日志记录 user_not_found |
| 密码错误 | 错误处理 | 返回401、日志记录 invalid_password |
| 账户禁用 | 状态检查 | 返回403、明确错误消息 |
| Token删除失败 | 事务回滚 | 整个登录事务回滚、无数据变更 |
| 登录时间更新失败 | 事务回滚 | 整个登录事务回滚、无数据变更 |

## Migration Notes

### 对现有代码的影响

**需要修改的文件**：
1. `backend/src/services/auth_service.py` - 添加事务管理、状态检查
2. `backend/src/api/auth.py` - 更新错误响应格式
3. `backend/src/core/security.py` - 添加日志记录

**不需要修改**：
- 数据库模型（无结构变更）
- API 端点路径（保持兼容）

### 前端适配

**需要修改的文件**：
1. `web/src/api/auth.ts` - 适配新的错误响应格式
2. `web/src/stores/user.ts` - 处理账户禁用错误
3. `web/src/views/Login.vue` - 显示友好错误消息

**错误处理示例**：

```typescript
// 登录失败处理
try {
  await authApi.login(credentials);
} catch (error) {
  const errorData = error.response.data;

  if (errorData.code === 'AUTH_ACCOUNT_DISABLED') {
    // 账户禁用：显示联系管理员提示
    showContactAdminMessage();
  } else if (errorData.code === 'AUTH_INVALID_CREDENTIALS') {
    // 密码错误：提示检查邮箱和密码
    showInvalidCredentialsMessage();
  }
}
```

## Testing

### 新增测试用例

```python
# tests/unit/test_auth_service.py
class TestLoginUser:
    def test_login_success(self, test_db):
        """✅ 正常登录成功"""
        pass

    def test_login_user_not_found(self, test_db):
        """✅ 用户不存在"""
        pass

    def test_login_wrong_password(self, test_db):
        """✅ 密码错误"""
        pass

    def test_login_disabled_account(self, test_db):
        """✅ 账户禁用"""
        pass

    def test_login_transaction_rollback_on_token_deletion_failure(self, test_db):
        """✅ 事务回滚（Token删除失败）"""
        pass

    def test_login_security_message_consistency(self, test_db):
        """✅ 安全性：用户不存在和密码错误返回相同消息"""
        # 用户不存在
        response1 = client.post("/api/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "password"
        })

        # 密码错误
        user = create_user(test_db, email="test@example.com", password="correct")
        response2 = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "wrong"
        })

        # 验证：返回相同的错误消息（安全考虑）
        assert response1.json()["message"] == response2.json()["message"]
        assert response1.json()["message"] == "邮箱或密码错误"
```

### 安全性测试

```python
def test_login_does_not_reveal_user_existence(test_db, test_client):
    """
    测试登录不泄露用户是否存在
    """
    # 尝试登录不存在的用户
    response1 = test_client.post("/api/auth/login", json={
        "email": "nonexistent@example.com",
        "password": "password"
    })

    # 创建用户后，使用错误密码登录
    create_user(test_db, email="test@example.com", password="correct")
    response2 = test_client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "wrong"
    })

    # 验证：错误消息相同，无法通过响应判断用户是否存在
    assert response1.status_code == response2.status_code == 401
    assert response1.json()["code"] == response2.json()["code"]
    assert "邮箱或密码错误" in response1.json()["message"]
```
