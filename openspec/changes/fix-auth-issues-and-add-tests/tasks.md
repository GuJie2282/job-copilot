## 实施任务清单

本文档列出修复认证系统问题并添加单元测试的所有实施任务。

## 1. 错误处理基础设施

- [x] 1.1 创建统一错误响应模型（ErrorResponse）
  - 创建 `backend/src/core/error_handler.py`
  - 定义 `ErrorResponse` Pydantic 模型（code、message、details、action）
  - 定义 `ErrorCode` 枚举类

- [x] 1.2 实现错误码体系
  - 定义所有错误码（AUTH_*、CODE_*、TOKEN_*、VALID_*、SYSTEM_*）
  - 创建错误消息映射字典
  - 添加单元测试验证错误码唯一性

- [x] 1.3 创建异常处理装饰器
  - 实现 `handle_errors` 装饰器
  - 自动转换异常为结构化错误响应
  - 添加异常链保留原始错误信息

## 2. 数据库事务管理

- [x] 2.1 优化注册流程事务
  - 重构 `register_user` 函数
  - 划分事务边界：验证码事务 + 用户创建事务
  - 添加事务回滚测试

- [x] 2.2 优化登录流程事务
  - 重构 `login_user` 函数
  - 使用单一事务完成：用户查询 + Token管理 + 时间更新
  - 添加事务回滚测试

- [x] 2.3 优化Token刷新事务
  - 重构 `refresh_token` 函数
  - 使用单一事务完成：Token验证 + 删除 + 创建
  - 添加事务回滚测试

- [ ] 2.4 添加事务超时保护
  - 实现 `transaction_with_timeout` 上下文管理器
  - 为所有事务添加5秒超时
  - 添加超时日志记录

## 3. 结构化日志

- [x] 3.1 配置日志系统
  - 创建 `backend/src/core/logging.py`
  - 实现 `JsonFormatter` 格式化器
  - 配置开发环境和生产环境日志

- [x] 3.2 添加敏感信息脱敏工具
  - 实现 `mask_email`、`mask_phone`、`mask_token`、`mask_code` 函数
  - 添加脱敏函数单元测试

- [x] 3.3 在注册流程添加日志
  - 添加注册开始/成功/失败日志
  - 添加关键步骤DEBUG日志
  - 使用脱敏函数保护敏感信息

- [x] 3.4 在登录流程添加日志
  - 添加登录尝试/成功/失败日志
  - 记录失败原因（user_not_found、invalid_password）
  - 记录账户禁用事件

- [x] 3.5 在Token刷新添加日志
  - 添加刷新尝试/成功/失败日志
  - 记录Token轮换信息（脱敏）
  - 记录失败原因

## 4. 边界情况处理

- [x] 4.1 完善注册边界情况
  - 实现邮箱已存在检查（AUTH_EMAIL_EXISTS）
  - 实现验证码无效/过期/已使用检查（CODE_*）
  - 实现密码长度验证（VALID_PASSWORD_*）
  - 实现手机号格式验证（VALID_PHONE_FORMAT）

- [x] 4.2 完善登录边界情况
  - 实现用户不存在处理（不区分消息，仅日志记录）
  - 实现密码错误处理（不区分消息，仅日志记录）
  - 实现账户禁用检查（AUTH_ACCOUNT_DISABLED）

- [x] 4.3 完善Token刷新边界情况
  - 实现Token无效处理（TOKEN_INVALID）
  - 实现Token过期处理（TOKEN_EXPIRED）
  - 自动删除过期Token

## 5. API层优化

- [x] 5.1 更新注册端点错误响应
  - 修改 `POST /api/auth/register` 端点
  - 使用统一错误响应格式
  - 添加详细日志

- [x] 5.2 更新登录端点错误响应
  - 修改 `POST /api/auth/login` 端点
  - 使用统一错误响应格式
  - 添加详细日志
  - 处理账户禁用情况（403状态码）

- [x] 5.3 更新Token刷新端点错误响应
  - 修改 `POST /api/auth/refresh` 端点
  - 使用统一错误响应格式
  - 添加详细日志
  - 区分Token无效和过期

## 6. 验证码服务优化

- [x] 6.1 优化验证码验证逻辑
  - 重构 `verify_code` 函数
  - 区分验证码错误类型（无效、过期、已使用）
  - 添加详细日志

- [x] 6.2 添加验证码状态检查
  - 实现 `is_valid()` 方法检查过期和已使用状态
  - 添加单元测试验证状态检查逻辑

## 7. 安全模块增强

- [x] 7.1 在安全模块添加日志
  - 在 `create_access_token` 添加日志
  - 在 `create_refresh_token` 添加日志
  - 在 `verify_password` 添加日志

## 8. 前端适配 - 错误处理

- [x] 8.1 更新注册错误处理
  - 修改 `web/src/api/auth.ts` 中的注册函数
  - 适配新的错误响应格式
  - 根据 `action` 字段自动处理错误

- [x] 8.2 更新登录错误处理
  - 修改 `web/src/api/auth.ts` 中的登录函数
  - 处理账户禁用错误（AUTH_ACCOUNT_DISABLED）
  - 显示友好错误消息

- [x] 8.3 更新Token刷新错误处理
  - 修改 `web/src/api/client.ts` 中的拦截器
  - 刷新失败时清空Token并跳转登录页
  - 添加错误提示

## 9. 前端适配 - Token刷新队列

- [x] 9.1 实现Token刷新队列
  - 修改 `web/src/api/client.ts`
  - 添加 `isRefreshing` 状态标记
  - 添加 `refreshSubscribers` 队列
  - 实现 `subscribeTokenRefresh` 函数

- [x] 9.2 添加刷新失败重试机制
  - 实现 `refreshWithRetry` 函数
  - 重试3次，间隔1秒
  - 网络错误重试，Token错误不重试

- [x] 9.3 测试并发刷新场景
  - 手动测试：快速发起多个需要Token的请求
  - 验证：只有一个刷新请求执行
  - 验证：所有请求等待刷新完成

## 10. 前端适配 - 字段命名修复

- [x] 10.1 统一前后端字段命名
  - 检查所有API调用
  - 确认前端使用 camelCase
  - 确认后端使用 snake_case
  - 在API层自动转换

## 11. 单元测试 - 认证服务

- [ ] 11.1 编写注册服务单元测试
  - 创建 `tests/unit/test_auth_service.py`
  - 测试：正常注册成功
  - 测试：邮箱已存在（AUTH_EMAIL_EXISTS）
  - 测试：验证码无效（CODE_INVALID）
  - 测试：验证码过期（CODE_EXPIRED）
  - 测试：验证码已使用（CODE_ALREADY_USED）
  - 测试：密码过长（VALID_PASSWORD_TOO_LONG）
  - 测试：事务回滚（用户创建失败）

- [ ] 11.2 编写登录服务单元测试
  - 测试：正常登录成功
  - 测试：用户不存在
  - 测试：密码错误
  - 测试：账户禁用（AUTH_ACCOUNT_DISABLED）
  - 测试：事务回滚（Token删除失败）
  - 测试：安全性（不泄露用户存在性）

- [ ] 11.3 编写Token刷新服务单元测试
  - 测试：正常刷新成功
  - 测试：Token无效（TOKEN_INVALID）
  - 测试：Token过期（TOKEN_EXPIRED）
  - 测试：事务回滚（新Token创建失败）
  - 测试：Token轮换（旧Token失效）

## 12. 单元测试 - 安全模块

- [ ] 12.1 编写安全工具单元测试
  - 创建 `tests/unit/test_security.py`
  - 测试：密码哈希和验证
  - 测试：Access Token生成和验证
  - 测试：Refresh Token生成和验证
  - 测试：Token过期验证

## 13. 单元测试 - 验证码服务

- [ ] 13.1 编写验证码服务单元测试
  - 创建 `tests/unit/test_code_service.py`
  - 测试：验证码生成（6位数字）
  - 测试：验证码验证（正确、错误、过期、已使用）
  - 测试：发送频率限制（5分钟内只能发送一次）

## 14. 单元测试 - 错误处理

- [ ] 14.1 编写错误处理单元测试
  - 创建 `tests/unit/test_error_handler.py`
  - 测试：错误码枚举唯一性
  - 测试：异常处理装饰器
  - 测试：错误响应格式

## 15. 单元测试 - 日志脱敏

- [ ] 15.1 编写脱敏函数单元测试
  - 创建 `tests/unit/test_logging.py`
  - 测试：邮箱脱敏
  - 测试：手机号脱敏
  - 测试：Token脱敏
  - 测试：验证码脱敏

## 16. 集成测试

- [ ] 16.1 编写注册流程集成测试
  - 创建 `tests/integration/test_register_flow.py`
  - 测试：完整注册流程（发送验证码 → 验证 → 注册 → Token）
  - 测试：验证码过期场景
  - 测试：验证码已使用场景

- [ ] 16.2 编写登录流程集成测试
  - 创建 `tests/integration/test_login_flow.py`
  - 测试：完整登录流程（登录 → Token → 受保护资源）
  - 测试：账户禁用场景
  - 测试：Token过期刷新场景

- [ ] 16.3 编写Token刷新集成测试
  - 创建 `tests/integration/test_token_refresh.py`
  - 测试：Token刷新流程
  - 测试：并发刷新请求
  - 测试：刷新失败重试

- [ ] 16.4 编写完整认证流程端到端测试
  - 创建 `tests/e2e/test_full_auth_flow.py`
  - 测试：注册 → 登录 → 刷新Token → 登出
  - 验证：每个步骤的数据正确性
  - 验证：Token有效性

## 17. 测试基础设施

- [ ] 17.1 配置测试框架
  - 创建 `tests/conftest.py`
  - 配置 pytest
  - 创建测试夹具（test_db、test_user、test_client）

- [ ] 17.2 配置测试覆盖率
  - 安装 pytest-cov
  - 配置覆盖率目标（核心模块 ≥90%）
  - 生成 HTML 覆盖率报告

## 18. 依赖更新

- [x] 18.1 添加测试依赖
  - 更新 `backend/requirements.txt`
  - 添加 pytest
  - 添加 pytest-asyncio
  - 添加 pytest-cov
  - 添加 httpx

- [x] 18.2 安装依赖
  - 创建虚拟环境（如不存在）
  - 安装所有依赖
  - 验证安装成功

## 19. 部署准备

- [ ] 19.1 备份数据库
  - 备份 `backend/job_copilot.db`
  - 验证备份文件完整性

- [ ] 19.2 创建迁移脚本
  - 创建数据库迁移检查脚本
  - 验证数据库结构兼容性

## 20. 部署和验证

- [x] 20.1 部署后端
  - 拉取最新代码
  - 安装依赖
  - 重启后端服务

- [ ] 20.2 部署前端
  - 拉取最新代码
  - 安装依赖
  - 构建前端
  - 部署到Web服务器

- [ ] 20.3 运行测试套件
  - 运行所有单元测试
  - 运行集成测试
  - 验证测试覆盖率
  - 查看测试报告

- [ ] 20.4 手动冒烟测试
  - 测试注册流程
  - 测试登录流程
  - 测试Token刷新
  - 测试边界情况（错误消息、友好提示）

- [ ] 20.5 监控日志
  - 检查启动日志
  - 验证结构化日志格式
  - 验证敏感信息已脱敏
  - 检查ERROR和WARNING日志

## 21. 文档更新

- [ ] 21.1 更新API文档
  - 更新 Swagger 文档
  - 添加错误响应示例
  - 添加错误码说明

- [ ] 21.2 更新项目文档
  - 更新 README.md
  - 添加优化说明
  - 更新部署指南

## 22. 归档

- [ ] 22.1 归档Change
  - 运行 `/opsx:archive`
  - 将specs同步到主文档
  - 清理change目录

## 任务统计

- **总任务数**：131个
- **预计总工时**：16-24小时
- **建议实施周期**：3-5个工作日

## 优先级说明

**P0（必须完成）**：
- 任务 1-7：错误处理、事务管理、日志、边界情况
- 任务 8-10：前端适配（错误处理、Token刷新队列）
- 任务 11-17：单元测试和集成测试

**P1（重要）**：
- 任务 18：依赖更新
- 任务 19-20：部署和验证

**P2（可选）**：
- 任务 21-22：文档更新和归档

## 风险提示

1. **数据迁移风险**：虽然无数据库结构变更，但建议先在开发环境验证
2. **前端兼容性**：确保所有API调用已适配新的错误响应格式
3. **测试覆盖率**：部署前务必运行完整测试套件，覆盖率需达标
4. **回滚准备**：保留数据库备份，准备回滚方案
