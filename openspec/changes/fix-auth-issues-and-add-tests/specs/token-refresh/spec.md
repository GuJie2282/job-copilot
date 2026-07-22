# Token Refresh Capability (DELTA)

## Overview

此文档定义了对 Token 刷新能力的 REQUIREMENTS 变更。这是对现有 `token-refresh` 规范的增量更新。

## 变更类型

**DELTA SPEC** - 此文档修改现有能力的要求

## New Requirements

### REQ-REFRESH-001: Token轮换原子性

Token刷新必须在单个事务内完成以下操作：

**要求**：
1. 验证旧 Refresh Token
2. 删除旧 Refresh Token
3. 创建新 Refresh Token
4. 所有操作在单个事务内完成

**事务边界**：

```python
def refresh_token(db: Session, refresh_token_str: str):
    """Token刷新 - 单事务完成"""
    # 验证Token签名（事务外）
    payload = verify_refresh_token(refresh_token_str)
    user_id = payload.get("user_id")

    # 事务：Token轮换
    with db.begin():
        # 1. 查询旧Token
        token_obj = db.query(RefreshToken).filter(
            RefreshToken.token == refresh_token_str,
            RefreshToken.user_id == user_id
        ).first()

        if not token_obj:
            raise HTTPException(
                status_code=401,
                detail={"code": "TOKEN_INVALID", "message": "Token无效"}
            )

        # 2. 检查Token是否过期
        if not token_obj.is_valid():
            db.delete(token_obj)  # 删除过期Token
            raise HTTPException(
                status_code=401,
                detail={"code": "TOKEN_EXPIRED", "message": "Token已过期"}
            )

        # 3. 删除旧Token
        db.delete(token_obj)

        # 4. 创建新Token
        new_refresh_token_str = create_refresh_token(data={"user_id": user_id})
        new_refresh_token_obj = RefreshToken(
            user_id=user_id,
            token=new_refresh_token_str,
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        db.add(new_refresh_token_obj)

    # 非事务：生成Access Token
    new_access_token = create_access_token(data={"user_id": user_id})

    return new_access_token, new_refresh_token_str
```

### REQ-REFRESH-002: 并发刷新请求处理

前端必须实现Token刷新队列机制，避免并发刷新请求：

**问题场景**：
```
时间线：
T0: 请求A失败（401）→ 触发刷新
T1: 请求B失败（401）→ 触发刷新  ← 并发刷新！
T2: 刷新A成功
T3: 刷新B成功（覆盖A）→ Token不一致
```

**前端解决方案**：

```typescript
// web/src/api/client.ts
let isRefreshing = false;
let refreshSubscribers: Array<(token: string) => void> = [];

function subscribeTokenRefresh(cb: (token: string) => void) {
  refreshSubscribers.push(cb);
}

function onTokenRefreshed(token: string) {
  refreshSubscribers.forEach(cb => cb(token));
  refreshSubscribers = [];
}

async function refreshAccessToken() {
  // 如果正在刷新，等待刷新完成
  if (isRefreshing) {
    return new Promise(resolve => {
      subscribeTokenRefresh(token => resolve(token));
    });
  }

  isRefreshing = true;
  try {
    const response = await authApi.refreshToken(refreshToken);
    const newToken = response.data.token;
    onTokenRefreshed(newToken);
    return newToken;
  } finally {
    isRefreshing = false;
  }
}
```

### REQ-REFRESH-003: 刷新失败重试机制

Token刷新失败时的处理策略：

**要求**：
1. Token无效/过期：清空本地Token，跳转登录页
2. 网络错误：重试3次，间隔1秒
3. 服务器错误：清空本地Token，跳转登录页

**实现示例**：

```typescript
async function refreshWithRetry(refreshToken: string, retries = 3): Promise<string> {
  for (let i = 0; i < retries; i++) {
    try {
      const response = await authApi.refreshToken(refreshToken);
      return response.data.token;
    } catch (error) {
      if (error.response?.status === 401) {
        // Token无效/过期，不再重试
        throw error;
      } else if (error.response?.status >= 500) {
        // 服务器错误，重试
        if (i < retries - 1) {
          await new Promise(resolve => setTimeout(resolve, 1000));
          continue;
        }
      }
      throw error;
    }
  }
  throw new Error('Token refresh failed after retries');
}
```

### REQ-REFRESH-004: 结构化日志

Token刷新流程必须记录详细日志：

```python
# 刷新尝试
logger.info(
    "token_refresh_attempt",
    extra={
        "user_id": user_id,
        "ip": request.client.host
    }
)

# 刷新成功
logger.info(
    "token_refresh_success",
    extra={
        "user_id": user_id,
        "old_token": mask_token(refresh_token_str),
        "new_token": mask_token(new_refresh_token),
        "duration_ms": duration_ms
    }
)

# 刷新失败
logger.warning(
    "token_refresh_failed",
    extra={
        "user_id": user_id,
        "reason": "token_expired",  # 或 token_invalid
        "ip": request.client.host
    }
)
```

### REQ-REFRESH-005: 错误响应规范

Token刷新失败时的错误响应：

| 场景 | 状态码 | 错误码 | 错误消息 | Action |
|------|--------|--------|----------|--------|
| Token无效 | 401 | TOKEN_INVALID | Token无效，请重新登录 | login |
| Token过期 | 401 | TOKEN_EXPIRED | Token已过期，请重新登录 | login |
| Token缺失 | 401 | TOKEN_MISSING | 未提供Token，请重新登录 | login |
| 数据库错误 | 500 | SYSTEM_DATABASE_ERROR | 系统错误，请稍后重试 | retry |

## Modified Requirements

### 修改：REQ-REFRESH-OLD-001（原始Token刷新流程）

**原始要求**：
- 刷新流程包含Token验证、删除旧Token、创建新Token

**新要求**：
- 刷新流程在单个事务内完成（验证、删除、创建）
- 前端实现刷新队列，避免并发刷新
- 刷新失败时智能重试

**变更原因**：
- 数据一致性问题（Token删除和创建不在同一事务）
- 并发问题（多个请求同时刷新导致Token不一致）
- 用户体验问题（刷新失败无重试机制）

### 修改：REQ-REFRESH-OLD-002（错误处理）

**原始要求**：
- 返回 401 错误和简单消息

**新要求**：
- 结构化错误响应（code、message、action）
- 区分Token无效和过期
- 前端智能处理（自动跳转登录页）

**变更原因**：
- 用户体验差（刷新失败无明确提示）
- 前端无法区分错误类型（无效 vs 过期）

## Implementation Notes

### Token刷新流程伪代码

```python
def refresh_token(db: Session, refresh_token_str: str, request: Request):
    start_time = time.time()

    try:
        # 验证Token签名（事务外）
        payload = verify_refresh_token(refresh_token_str)
        user_id = payload.get("user_id")

        logger.info("token_refresh_attempt", extra={
            "user_id": user_id,
            "ip": request.client.host
        })

        # 事务：Token轮换
        with db.begin():
            # 1. 查询旧Token
            token_obj = db.query(RefreshToken).filter(
                RefreshToken.token == refresh_token_str,
                RefreshToken.user_id == user_id
            ).first()

            if not token_obj:
                logger.warning("token_refresh_failed", extra={
                    "user_id": user_id,
                    "reason": "token_not_found",
                    "ip": request.client.host
                })
                raise HTTPException(
                    status_code=401,
                    detail={
                        "code": "TOKEN_INVALID",
                        "message": "Token无效，请重新登录",
                        "action": "login"
                    }
                )

            # 2. 检查Token是否过期
            if not token_obj.is_valid():
                logger.warning("token_refresh_failed", extra={
                    "user_id": user_id,
                    "reason": "token_expired",
                    "ip": request.client.host
                })
                # 删除过期Token
                db.delete(token_obj)
                raise HTTPException(
                    status_code=401,
                    detail={
                        "code": "TOKEN_EXPIRED",
                        "message": "Token已过期，请重新登录",
                        "action": "login"
                    }
                )

            # 3. 删除旧Token
            db.delete(token_obj)

            # 4. 创建新Token
            new_refresh_token_str = create_refresh_token(data={"user_id": user_id})
            new_refresh_token_obj = RefreshToken(
                user_id=user_id,
                token=new_refresh_token_str,
                expires_at=datetime.utcnow() + timedelta(days=7)
            )
            db.add(new_refresh_token_obj)

        # 非事务：生成Access Token
        new_access_token = create_access_token(data={"user_id": user_id})

        duration_ms = (time.time() - start_time) * 1000

        logger.info("token_refresh_success", extra={
            "user_id": user_id,
            "old_token": mask_token(refresh_token_str),
            "new_token": mask_token(new_refresh_token_str),
            "duration_ms": duration_ms
        })

        return new_access_token, new_refresh_token_str

    except HTTPException:
        raise
    except Exception as e:
        logger.error("token_refresh_error", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"code": "SYSTEM_INTERNAL_ERROR", "message": "系统错误"}
        )
```

### 测试矩阵

| 测试场景 | 验证点 | 期望结果 |
|----------|--------|----------|
| 正常刷新 | 事务完整性 | 旧Token删除、新Token创建 |
| Token无效 | 错误处理 | 返回401、TOKEN_INVALID |
| Token过期 | 错误处理 | 返回401、TOKEN_EXPIRED、旧Token删除 |
| Token删除失败 | 事务回滚 | 整个事务回滚、旧Token仍有效 |
| 新Token创建失败 | 事务回滚 | 整个事务回滚、旧Token仍有效 |
| 并发刷新 | 队列处理 | 只有一个刷新请求成功，其他等待 |

## Migration Notes

### 对现有代码的影响

**需要修改的文件**：
1. `backend/src/services/auth_service.py` - 添加事务管理
2. `backend/src/api/auth.py` - 更新错误响应格式
3. `backend/src/core/security.py` - 添加日志记录

**不需要修改**：
- 数据库模型（无结构变更）
- API 端点路径（保持兼容）

### 前端适配

**需要修改的文件**：
1. `web/src/api/client.ts` - 实现刷新队列和重试逻辑
2. `web/src/stores/user.ts` - 处理刷新失败
3. `web/src/router/index.ts` - 刷新失败时跳转登录页

**错误处理示例**：

```typescript
// Token刷新拦截器
axios.interceptors.response.use(
  response => response,
  async error => {
    const originalRequest = error.config;

    // 如果是401错误且未重试过
    if (error.response?.status === 401 && !originalRequest._isRetry) {
      originalRequest._isRetry = true;

      try {
        // 刷新Token
        const newToken = await refreshAccessToken();

        // 重试原请求
        originalRequest.headers['Authorization'] = `Bearer ${newToken}`;
        return axios(originalRequest);

      } catch (refreshError) {
        // 刷新失败，清空Token并跳转登录页
        userStore.clearTokens();
        router.push('/login');
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);
```

## Testing

### 新增测试用例

```python
# tests/unit/test_auth_service.py
class TestRefreshToken:
    def test_refresh_success(self, test_db):
        """✅ 正常刷新成功"""
        pass

    def test_refresh_invalid_token(self, test_db):
        """✅ Token无效"""
        pass

    def test_refresh_expired_token(self, test_db):
        """✅ Token过期"""
        pass

    def test_refresh_transaction_rollback_on_creation_failure(self, test_db):
        """✅ 事务回滚（新Token创建失败）"""
        pass

    def test_refresh_token_rotation(self, test_db):
        """✅ Token轮换（旧Token失效）"""
        pass
```

### 并发测试

```python
# tests/integration/test_token_refresh.py
def test_concurrent_refresh_requests(test_client, test_user):
    """
    测试并发刷新请求
    验证：只有一个刷新请求成功，其他等待或返回相同Token
    """
    refresh_token = create_refresh_token(test_db, test_user.id)

    import threading
    results = []
    errors = []

    def refresh():
        try:
            response = test_client.post("/api/auth/refresh", json={
                "refresh_token": refresh_token.token
            })
            results.append(response.json())
        except Exception as e:
            errors.append(e)

    # 模拟10个并发刷新请求
    threads = [threading.Thread(target=refresh) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # 验证：至少有一个成功
    assert len(results) >= 1

    # 验证：所有成功的请求返回相同的Token
    successful_tokens = [r["token"] for r in results]
    assert len(set(successful_tokens)) == 1  # 所有Token相同

    # 验证：数据库中只有一个有效Token
    tokens = test_db.query(RefreshToken).filter(
        RefreshToken.user_id == str(test_user.id)
    ).all()
    assert len(tokens) == 1
```

### 前端测试

```typescript
// tests/unit/client.spec.ts
describe('Token Refresh Queue', () => {
  it('should queue concurrent refresh requests', async () => {
    // Mock token refresh API
    mockApi.refreshToken.mockResolvedValue({
      data: { token: 'new-token', refreshToken: 'new-refresh-token' }
    });

    // 触发3个并发刷新请求
    const promises = [
      refreshAccessToken(),
      refreshAccessToken(),
      refreshAccessToken()
    ];

    const results = await Promise.all(promises);

    // 验证：API只调用一次
    expect(mockApi.refreshToken).toHaveBeenCalledTimes(1);

    // 验证：所有请求返回相同的Token
    expect(results[0]).toEqual(results[1]);
    expect(results[1]).toEqual(results[2]);
  });

  it('should redirect to login on refresh failure', async () => {
    // Mock token refresh failure
    mockApi.refreshToken.mockRejectedValue({
      response: { status: 401, data: { code: 'TOKEN_EXPIRED' } }
    });

    // 尝试刷新
    await expect(refreshAccessToken()).rejects.toMatchObject({
      response: { status: 401 }
    });

    // 验证：清空Token
    expect(userStore.token).toBeNull();
    expect(userStore.refreshToken).toBeNull();

    // 验证：跳转登录页
    expect(router.push).toHaveBeenCalledWith('/login');
  });
});
```
