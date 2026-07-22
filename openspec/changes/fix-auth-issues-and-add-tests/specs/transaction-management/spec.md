# Transaction Management Capability

## Overview

数据库事务管理规范，确保所有涉及多步操作的认证流程保持数据一致性和原子性。

## Requirements

### REQ-1: 事务边界定义

每个认证流程必须明确定义事务边界，确保相关操作的原子性。

**注册流程事务边界**：

```
事务1: 验证码验证
  - 查询验证码
  - 验证有效期和状态
  - 标记为已使用
  - 提交事务

事务2: 用户创建
  - 哈希密码
  - 创建用户记录
  - 提交事务

非事务: Token生成（JWT无需数据库）
```

**登录流程事务边界**：

```
事务1: 用户认证
  - 查询用户
  - 验证密码
  - 删除旧 Refresh Token（单设备登录）
  - 创建新 Refresh Token
  - 更新最后登录时间
  - 提交事务

非事务: Access Token生成（JWT无需数据库）
```

**Token刷新流程事务边界**：

```
事务1: Token轮换
  - 验证旧 Refresh Token
  - 删除旧 Refresh Token
  - 创建新 Refresh Token
  - 提交事务

非事务: Access Token生成（JWT无需数据库）
```

### REQ-2: 事务实现方式

使用 SQLAlchemy 的上下文管理器确保事务自动提交或回滚：

```python
def register_user(db: Session, register_data: RegisterRequest) -> User:
    """
    用户注册 - 使用事务保护
    """
    # 事务1: 验证码验证
    with db.begin():
        verification_code = db.query(VerificationCode).filter(
            VerificationCode.email == register_data.email,
            VerificationCode.code == register_data.verification_code
        ).first()

        if not verification_code:
            raise HTTPException(
                status_code=400,
                detail={"code": "CODE_INVALID", "message": "验证码无效"}
            )

        if not verification_code.is_valid():
            if verification_code.used:
                raise HTTPException(
                    status_code=400,
                    detail={"code": "CODE_ALREADY_USED", "message": "验证码已使用"}
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail={"code": "CODE_EXPIRED", "message": "验证码已过期"}
                )

        # 标记验证码为已使用
        verification_code.used = True
        db.flush()  # 刷新到数据库，但不提交

    # 事务2: 用户创建
    with db.begin():
        # 检查邮箱是否已存在（双重检查）
        existing_user = db.query(User).filter(
            User.email == register_data.email
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail={"code": "AUTH_EMAIL_EXISTS", "message": "该邮箱已被注册"}
            )

        # 哈希密码
        password_hash = get_password_hash(register_data.password)

        # 创建用户
        new_user = User(
            name=register_data.name,
            email=register_data.email,
            phone=register_data.phone,
            password_hash=password_hash,
            is_verified=True,
            is_active=True
        )
        db.add(new_user)
        db.flush()

    # 非事务操作：Token生成（失败不影响用户创建）
    try:
        access_token = create_access_token(data={
            "user_id": str(new_user.id),
            "email": new_user.email
        })
        refresh_token_str = create_refresh_token(data={"user_id": str(new_user.id)})

        # 存储 Refresh Token（独立事务）
        with db.begin():
            refresh_token_obj = RefreshToken(
                user_id=str(new_user.id),
                token=refresh_token_str,
                expires_at=datetime.utcnow() + timedelta(days=7)
            )
            db.add(refresh_token_obj)
    except Exception as e:
        # Token生成失败，但用户已创建（可重新登录获取Token）
        logger.error(f"Token生成失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"code": "SYSTEM_INTERNAL_ERROR", "message": "系统错误，请重新登录"}
        )

    return new_user
```

### REQ-3: 事务回滚测试

所有事务操作必须有对应的回滚测试用例：

```python
def test_register_transaction_rollback_on_user_creation_failure(db):
    """
    测试用户创建失败时的回滚
    验证码应保持未使用状态
    """
    # 准备：创建验证码
    code = VerificationCode(
        email="test@example.com",
        code="123456",
        expires_at=datetime.utcnow() + timedelta(minutes=5)
    )
    db.add(code)
    db.commit()

    # 模拟：用户创建失败（如数据库约束违反）
    with pytest.raises(IntegrityError):
        with db.begin():
            # 标记验证码为已使用
            code.used = True
            db.flush()

            # 模拟用户创建失败
            user = User(
                email="test@example.com",
                password_hash="hash",
                # 缺少必填字段
            )
            db.add(user)
            db.flush()

    # 验证：验证码应该回滚（未使用）
    db.refresh(code)
    assert code.used == False
```

### REQ-4: 事务超时保护

为防止长事务锁定数据库，添加事务超时机制：

```python
from contextlib import contextmanager
from signal import signal, SIGALRM, default_int_handler

@contextmanager
def transaction_with_timeout(db: Session, timeout_seconds: int = 5):
    """
    带超时的事务上下文管理器
    """
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Transaction timeout after {timeout_seconds} seconds")

    # 设置超时信号
    old_handler = signal(SIGALRM, timeout_handler)
    signal.alarm(timeout_seconds)

    try:
        with db.begin():
            yield
    finally:
        # 恢复原信号处理器
        signal.alarm(0)
        signal(SIGALRM, old_handler)

# 使用示例
def register_user(db: Session, register_data: RegisterRequest):
    with transaction_with_timeout(db, timeout_seconds=5):
        # 业务逻辑
        pass
```

### REQ-5: 事务隔离级别

SQLite 默认使用 **SERIALIZABLE** 隔离级别，已满足需求。

生产环境迁移到 PostgreSQL 时，使用 **READ COMMITTED**：

```python
# PostgreSQL 事务配置
engine = create_engine(
    DATABASE_URL,
    isolation_level="READ COMMITTED"  # 平衡性能和一致性
)
```

## Examples

### 示例1: 注册流程事务处理

**场景**：用户注册时验证码验证成功，但用户创建失败

**预期行为**：
1. 事务1（验证码标记）成功提交
2. 事务2（用户创建）失败回滚
3. 用户收到错误提示
4. 验证码已标记为已使用（可重新发送验证码）

**测试代码**：
```python
def test_register_verification_code_consumed_on_failure(db, client):
    """
    测试用户创建失败时验证码的状态
    """
    # 准备：发送验证码
    send_verification_code(db, "test@example.com")
    code = get_latest_code(db, "test@example.com")

    # 执行：注册时模拟用户创建失败
    with patch('src.services.auth_service.User') as MockUser:
        MockUser.side_effect = IntegrityError("mock error", {}, None)

        response = client.post("/api/auth/register", json={
            "email": "test@example.com",
            "password": "password123",
            "verification_code": code.code
        })

    # 验证
    assert response.status_code == 500
    db.refresh(code)
    assert code.used == True  # 验证码已被使用
```

### 示例2: 登录流程事务处理

**场景**：用户登录时删除旧 Token 失败

**预期行为**：
1. 整个登录事务回滚
2. 用户收到错误提示
3. 数据库状态不变（旧 Token 仍有效）

**测试代码**：
```python
def test_login_rollback_on_token_deletion_failure(db, client, user):
    """
    测试登录时 Token 删除失败的回滚
    """
    # 准备：创建用户的 Refresh Token
    existing_token = RefreshToken(
        user_id=str(user.id),
        token="existing-token",
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(existing_token)
    db.commit()

    # 执行：模拟删除失败
    with patch.object(db, 'execute') as mock_execute:
        mock_execute.side_effect = DatabaseError("mock error")

        response = client.post("/api/auth/login", json={
            "email": user.email,
            "password": "password"
        })

    # 验证
    assert response.status_code == 500
    # 旧 Token 应该仍存在
    tokens = db.query(RefreshToken).filter(
        RefreshToken.user_id == str(user.id)
    ).all()
    assert len(tokens) == 1
    assert tokens[0].token == "existing-token"
```

### 示例3: Token刷新流程事务处理

**场景**：Token刷新时删除旧 Token 成功，但创建新 Token 失败

**预期行为**：
1. 整个事务回滚
2. 旧 Token 恢复有效
3. 用户可重试刷新

**测试代码**：
```python
def test_token_refresh_rollback_on_creation_failure(db, client, refresh_token):
    """
    测试 Token 刷新时新 Token 创建失败的回滚
    """
    # 执行：模拟创建新 Token 失败
    with patch('src.services.auth_service.create_refresh_token') as mock_create:
        mock_create.side_effect = Exception("mock error")

        response = client.post("/api/auth/refresh", json={
            "refresh_token": refresh_token.token
        })

    # 验证
    assert response.status_code == 500
    # 旧 Token 应该仍存在
    db.refresh(refresh_token)
    assert refresh_token.is_valid()
```

## Implementation Notes

### 事务管理最佳实践

1. **保持事务简短**：事务中只包含必要的数据库操作
2. **避免嵌套事务**：使用扁平化的事务结构
3. **早验证、早返回**：在事务外验证输入，减少事务失败概率
4. **日志记录**：记录事务开始、提交、回滚事件

### 性能考虑

- SQLite 的 SERIALIZABLE 级别在高并发时可能锁定数据库
- 使用 WAL 模式提升并发性能：
  ```python
  # 启用 WAL 模式
  engine = create_engine(
      DATABASE_URL,
      connect_args={"check_same_thread": False}
  )
  with engine.connect() as conn:
      conn.execute(text("PRAGMA journal_mode=WAL"))
  ```

### 监控和告警

- 记录事务执行时间（超过1秒告警）
- 记录事务回滚次数（频繁回滚可能表明逻辑问题）
- 监控长事务（超过5秒的事务）

## Testing

### 测试要求

1. **单元测试**：每个事务操作必须有成功和失败场景的测试
2. **回滚测试**：验证失败场景下的数据回滚
3. **并发测试**：验证多线程/多进程下的事务隔离性
4. **性能测试**：验证事务执行时间在可接受范围内

### 测试覆盖率要求

- 事务操作覆盖率：100%
- 回滚场景覆盖率：100%
- 边界情况覆盖率：>80%

### 测试工具

- `pytest`：测试框架
- `pytest-asyncio`：异步测试
- `pytest-cov`：覆盖率报告
- `freezegun`：时间相关测试（验证码过期）
