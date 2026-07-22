# Auth Testing Capability

## Overview

认证模块测试规范，确保所有认证功能有充分的测试覆盖，保障系统质量和重构信心。

## Requirements

### REQ-1: 测试金字塔结构

采用测试金字塔策略，70% 单元测试 + 20% 集成测试 + 10% 端到端测试：

```
tests/
├── unit/                          # 单元测试（70%）
│   ├── test_security.py           # 密码哈希、JWT生成/验证
│   ├── test_code_service.py       # 验证码逻辑
│   ├── test_auth_service.py       # 认证业务逻辑
│   ├── test_error_handler.py      # 错误处理
│   └── test_transaction.py        # 事务管理
│
├── integration/                    # 集成测试（20%）
│   ├── test_register_flow.py      # 完整注册流程
│   ├── test_login_flow.py         # 完整登录流程
│   ├── test_token_refresh.py      # Token刷新流程
│   └── test_code_send_flow.py    # 验证码发送流程
│
└── e2e/                           # 端到端测试（10%）
    └── test_full_auth_flow.py    # 完整认证流程
```

### REQ-2: 测试覆盖率要求

| 模块 | 覆盖率目标 | 说明 |
|------|-----------|------|
| 核心业务逻辑（auth_service） | ≥90% | 关键路径必须有测试 |
| 工具函数（security） | ≥95% | 纯函数应100%覆盖 |
| API 层（auth.py） | ≥75% | 覆盖主要端点和错误场景 |
| 事务管理 | 100% | 所有事务必须有回滚测试 |
| 错误处理 | ≥85% | 覆盖主要错误场景 |

### REQ-3: 单元测试规范

#### 3.1 测试命名规范

使用 `test_<功能>_<场景>_<期望结果>` 格式：

```python
def test_register_user_with_valid_data_should_succeed():
    """✅ 正常注册成功"""
    pass

def test_register_user_with_existing_email_should_fail():
    """✅ 邮箱已存在"""
    pass

def test_register_user_with_invalid_code_should_fail():
    """✅ 验证码无效"""
    pass

def test_register_user_with_expired_code_should_fail():
    """✅ 验证码过期"""
    pass
```

#### 3.2 测试结构（AAA模式）

每个测试遵循 AAA（Arrange-Act-Assert）模式：

```python
def test_register_user_with_existing_email():
    # Arrange（准备）
    db = TestSession()
    existing_user = create_user(db, email="test@example.com")
    register_data = RegisterRequest(
        email="test@example.com",
        password="password123",
        verification_code="123456"
    )

    # Act（执行）
    with pytest.raises(HTTPException) as exc_info:
        register_user(db, register_data)

    # Assert（断言）
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["code"] == "AUTH_EMAIL_EXISTS"
    assert "action" in exc_info.value.detail
```

#### 3.3 Fixtures（测试夹具）

创建常用的测试夹具：

```python
# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from src.models.base import Base
from src.models.user import User, VerificationCode

@pytest.fixture
def test_db():
    """创建测试数据库"""
    # 使用内存数据库
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    with Session(engine) as session:
        yield session

    # 清理
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def test_user(test_db):
    """创建测试用户"""
    user = User(
        name="测试用户",
        email="test@example.com",
        password_hash="hashed_password",
        is_active=True
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user

@pytest.fixture
def test_verification_code(test_db):
    """创建测试验证码"""
    from datetime import datetime, timedelta

    code = VerificationCode(
        email="test@example.com",
        code="123456",
        expires_at=datetime.utcnow() + timedelta(minutes=5)
    )
    test_db.add(code)
    test_db.commit()
    test_db.refresh(code)
    return code

@pytest.fixture
def test_client(test_db):
    """创建测试客户端"""
    from fastapi.testclient import TestClient
    from src.main import app

    # 覆盖数据库依赖
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    from src.models.base import get_db
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
```

### REQ-4: 集成测试规范

集成测试验证完整业务流程：

```python
# tests/integration/test_register_flow.py
def test_register_flow_success(test_client):
    """
    测试完整注册流程：
    1. 发送验证码
    2. 验证验证码
    3. 注册用户
    4. 验证 Token
    """
    # 1. 发送验证码
    response = test_client.post("/api/auth/send-code", json={
        "email": "new@example.com"
    })
    assert response.status_code == 200

    # 2. 获取验证码（从测试数据库）
    code = get_latest_code(test_db, "new@example.com")
    assert code is not None

    # 3. 注册用户
    response = test_client.post("/api/auth/register", json={
        "name": "新用户",
        "email": "new@example.com",
        "password": "password123",
        "verification_code": code.code
    })
    assert response.status_code == 201
    data = response.json()
    assert "token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == "new@example.com"

    # 4. 验证 Token
    response = test_client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {data['token']}"}
    )
    assert response.status_code == 200
```

### REQ-5: 边界情况测试

必须覆盖以下边界情况：

#### 5.1 注册边界情况

```python
def test_register_with_very_long_password():
    """测试密码过长（超过72字节）"""
    response = test_client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "a" * 100,  # 超过72字节
        "verification_code": "123456"
    })
    assert response.status_code == 400
    assert "密码过长" in response.json()["message"]

def test_register_with_expired_code():
    """测试验证码过期"""
    # 创建过期验证码
    create_code(test_db, email="test@example.com", expired=True)

    response = test_client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "password123",
        "verification_code": "123456"
    })
    assert response.status_code == 400
    assert response.json()["code"] == "CODE_EXPIRED"

def test_register_with_used_code():
    """测试验证码已使用"""
    # 创建已使用的验证码
    code = create_code(test_db, email="test@example.com")
    code.used = True
    test_db.commit()

    response = test_client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "password123",
        "verification_code": code.code
    })
    assert response.status_code == 400
    assert response.json()["code"] == "CODE_ALREADY_USED"
```

#### 5.2 登录边界情况

```python
def test_login_with_nonexistent_user():
    """测试用户不存在"""
    response = test_client.post("/api/auth/login", json={
        "email": "nonexistent@example.com",
        "password": "password123"
    })
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_INVALID_CREDENTIALS"

def test_login_with_wrong_password():
    """测试密码错误"""
    user = create_user(test_db, email="test@example.com", password="correct")

    response = test_client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "wrong"  # 错误密码
    })
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_INVALID_CREDENTIALS"

def test_login_with_disabled_account():
    """测试账户禁用"""
    user = create_user(
        test_db,
        email="test@example.com",
        password="password",
        is_active=False
    )

    response = test_client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "password"
    })
    assert response.status_code == 403
    assert response.json()["code"] == "AUTH_ACCOUNT_DISABLED"
```

#### 5.3 Token刷新边界情况

```python
def test_refresh_with_invalid_token():
    """测试无效 Token"""
    response = test_client.post("/api/auth/refresh", json={
        "refresh_token": "invalid-token"
    })
    assert response.status_code == 401
    assert response.json()["code"] == "TOKEN_INVALID"

def test_refresh_with_expired_token():
    """测试过期 Token"""
    token = create_refresh_token(
        test_db,
        user_id="123",
        expired=True
    )

    response = test_client.post("/api/auth/refresh", json={
        "refresh_token": token.token
    })
    assert response.status_code == 401
    assert response.json()["code"] == "TOKEN_EXPIRED"

def test_refresh_concurrent_requests():
    """测试并发刷新请求"""
    user = create_user_with_refresh_token(test_db)

    # 模拟并发刷新
    import threading

    results = []
    def refresh():
        response = test_client.post("/api/auth/refresh", json={
            "refresh_token": user.refresh_token
        })
        results.append(response.json())

    threads = [threading.Thread(target=refresh) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # 验证：只有一个成功，其他失败或返回相同Token
    successful = [r for r in results if r.get("token")]
    assert len(successful) >= 1
```

### REQ-6: 事务回滚测试

所有事务必须有回滚测试：

```python
def test_register_transaction_rollback_on_user_creation_failure():
    """
    测试用户创建失败时的回滚
    验证码应保持未使用状态
    """
    # 准备
    code = create_code(test_db, email="test@example.com")

    # 模拟用户创建失败
    with patch('src.services.auth_service.User') as MockUser:
        MockUser.side_effect = IntegrityError("mock error", {}, None)

        with pytest.raises(IntegrityError):
            register_user(test_db, RegisterRequest(
                email="test@example.com",
                password="password123",
                verification_code=code.code
            ))

    # 验证：验证码应该回滚（未使用）
    test_db.refresh(code)
    assert code.used == False

def test_login_transaction_rollback_on_token_failure():
    """
    测试登录时 Token 创建失败的回滚
    数据库应保持原状态（无新Token）
    """
    user = create_user(test_db, email="test@example.com")

    # 模拟 Token 创建失败
    with patch('src.services.auth_service.create_refresh_token') as mock_create:
        mock_create.side_effect = Exception("mock error")

        with pytest.raises(Exception):
            login_user(test_db, LoginRequest(
                email="test@example.com",
                password="password"
            ))

    # 验证：无新 Token
    tokens = test_db.query(RefreshToken).filter(
        RefreshToken.user_id == str(user.id)
    ).all()
    assert len(tokens) == 0
```

### REQ-7: Mock和Patch策略

合理使用 mock 避免依赖外部服务：

```python
from unittest.mock import patch, MagicMock

def test_send_verification_code_with_mock_email():
    """测试验证码发送（Mock邮件服务）"""
    with patch('src.services.code_service.send_email') as mock_send:
        mock_send.return_value = None

        send_verification_code(test_db, "test@example.com")

        # 验证：邮件服务被调用
        mock_send.assert_called_once()

        # 验证：验证码已创建
        code = get_latest_code(test_db, "test@example.com")
        assert code is not None

def test_login_with_mock_time():
    """测试登录（Mock时间）"""
    from freezegun import freeze_time

    with freeze_time("2025-01-01 10:00:00"):
        user = login_user(test_db, LoginRequest(...))
        # 验证：登录时间为指定时间
        assert user.last_login == datetime(2025, 1, 1, 10, 0, 0)
```

## Examples

### 示例1: 完整的单元测试

```python
# tests/unit/test_auth_service.py
class TestAuthService:
    def test_register_user_success(self, test_db):
        """✅ 正常注册成功"""
        # Arrange
        code = create_code(test_db, email="test@example.com")
        register_data = RegisterRequest(
            name="张三",
            email="test@example.com",
            password="password123",
            verification_code=code.code
        )

        # Act
        user = register_user(test_db, register_data)

        # Assert
        assert user.email == "test@example.com"
        assert user.name == "张三"
        assert user.is_verified == True
        assert user.is_active == True

        # 验证码被标记为已使用
        test_db.refresh(code)
        assert code.used == True

    def test_register_user_email_exists(self, test_db):
        """✅ 邮箱已存在"""
        # Arrange
        existing_user = create_user(test_db, email="test@example.com")
        code = create_code(test_db, email="test@example.com")
        register_data = RegisterRequest(
            email="test@example.com",
            password="password123",
            verification_code=code.code
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            register_user(test_db, register_data)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["code"] == "AUTH_EMAIL_EXISTS"
        assert "action" in exc_info.value.detail

    def test_register_user_code_invalid(self, test_db):
        """✅ 验证码无效"""
        # Arrange
        register_data = RegisterRequest(
            email="test@example.com",
            password="password123",
            verification_code="wrong-code"  # 错误验证码
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            register_user(test_db, register_data)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["code"] == "CODE_INVALID"

    def test_register_user_code_expired(self, test_db):
        """✅ 验证码过期"""
        # Arrange
        code = VerificationCode(
            email="test@example.com",
            code="123456",
            expires_at=datetime.utcnow() - timedelta(minutes=1),  # 过期
            used=False
        )
        test_db.add(code)
        test_db.commit()

        register_data = RegisterRequest(
            email="test@example.com",
            password="password123",
            verification_code=code.code
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            register_user(test_db, register_data)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["code"] == "CODE_EXPIRED"
```

### 示例2: 完整的集成测试

```python
# tests/integration/test_full_flow.py
def test_complete_auth_flow(test_client, test_db):
    """
    测试完整认证流程：
    1. 发送验证码 → 注册 → 登录 → 刷新Token → 登出
    """
    # 1. 发送验证码
    response = test_client.post("/api/auth/send-code", json={
        "email": "new@example.com"
    })
    assert response.status_code == 200

    code = get_latest_code(test_db, "new@example.com")

    # 2. 注册
    response = test_client.post("/api/auth/register", json={
        "name": "新用户",
        "email": "new@example.com",
        "password": "password123",
        "verification_code": code.code
    })
    assert response.status_code == 201
    register_data = response.json()
    access_token = register_data["token"]
    refresh_token = register_data["refresh_token"]

    # 3. 验证登录状态
    response = test_client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "new@example.com"

    # 4. 刷新Token
    response = test_client.post("/api/auth/refresh", json={
        "refresh_token": refresh_token
    })
    assert response.status_code == 200
    refresh_data = response.json()
    new_access_token = refresh_data["token"]
    new_refresh_token = refresh_data["refresh_token"]

    # 新Token有效
    response = test_client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {new_access_token}"}
    )
    assert response.status_code == 200

    # 5. 登出
    response = test_client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {new_access_token}"}
    )
    assert response.status_code == 200

    # 6. 验证登出后Token失效
    response = test_client.post("/api/auth/refresh", json={
        "refresh_token": new_refresh_token
    })
    assert response.status_code == 401
```

## Implementation Notes

### 测试运行

```bash
# 运行所有测试
pytest tests/

# 运行特定测试
pytest tests/unit/test_auth_service.py

# 生成覆盖率报告
pytest tests/ --cov=src --cov-report=html

# 查看覆盖率报告
# 打开 htmlcov/index.html
```

### CI/CD集成

在 `.github/workflows/tests.yml` 中配置：

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: pytest tests/ --cov=src --cov-report=xml
      - uses: codecov/codecov-action@v2
```

### 测试最佳实践

1. **独立性**：每个测试独立运行，不依赖其他测试
2. **快速**：单元测试应快速执行（<100ms）
3. **可读性**：测试代码应清晰、自解释
4. **维护性**：避免硬编码，使用 fixture
5. **真实性**：集成测试使用真实场景

## Testing

### 测试要求

1. **覆盖率达标**：核心模块 ≥90%
2. **所有测试通过**：无失败、无跳过
3. **测试时间合理**：完整测试套件 <5分钟
4. **CI/CD通过**：自动化测试必须通过

### 测试工具

- `pytest`：测试框架
- `pytest-cov`：覆盖率报告
- `pytest-asyncio`：异步测试
- `freezegun`：时间Mock
- `unittest.mock`：Mock和Patch
