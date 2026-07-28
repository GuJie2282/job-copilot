# Spec Delta: 模拟面试（mock-interview）— 异步开局

## ADDED Requirements

### Requirement: 异步开局（出题不阻塞创建请求）

系统 SHALL 在创建面试会话时立即返回会话标识，将出题（session_setup）移至后台执行；客户端 SHALL 通过轮询会话状态获取第一题，出题期间显示出题就绪等待态。

#### Scenario: 立即返回会话标识
- **WHEN** 客户端请求创建面试会话且画像就绪
- **THEN** 系统 SHALL 立即返回会话标识与「出题中」状态
- **AND** 系统 SHALL NOT 在该请求内同步完成出题

#### Scenario: 后台出题就绪
- **WHEN** 后台出题完成、状态机抵达第一个等待点
- **THEN** 系统 SHALL 将会话状态置为「面试中」
- **AND** 系统 SHALL 使第一题可经查询会话状态获得

#### Scenario: 出题中等待态
- **WHEN** 客户端查询处于「出题中」的会话
- **THEN** 系统 SHALL 返回「出题中」状态且当前问题为空
- **AND** 客户端 SHALL 显示出题就绪等待反馈并继续轮询

#### Scenario: 后台出题失败
- **WHEN** 后台出题过程抛出异常
- **THEN** 系统 SHALL 将会话状态置为错误态并记录可读原因
- **AND** 客户端轮询 SHALL 获得错误态与原因，而非泛化的请求失败

#### Scenario: 画像缺失仍同步返回
- **WHEN** 客户端请求创建面试会话但画像缺失
- **THEN** 系统 SHALL 在创建请求内同步返回画像缺失错误
- **AND** 系统 SHALL NOT 启动后台出题任务

## MODIFIED Requirements

### Requirement: 会话式 API

系统 SHALL 提供会话式 API 支持长程面试交互；创建会话端点采用异步开局——立即返回会话标识与「出题中」状态，第一题经查询会话状态获取；答题端点采用多态响应。

#### Scenario: 创建会话（异步开局）
- **WHEN** 客户端请求创建面试会话（含配置参数，画像就绪）
- **THEN** 响应 SHALL 立即包含会话标识与状态「出题中」
- **AND** 响应 SHALL NOT 阻塞等待第一题生成

#### Scenario: 查询会话拿第一题
- **WHEN** 客户端轮询查询处于「出题中」的会话，直至出题完成
- **THEN** 响应 SHALL 包含状态「面试中」与第一题内容
- **AND** 客户端 SHALL 据此进入答题交互

#### Scenario: 提交回答（面试继续）
- **WHEN** 客户端提交一轮回答且面试未结束
- **THEN** 响应 SHALL 包含状态为「面试中」、当前轮次、下一题内容
- **AND** 当处于教练模式时，响应 SHALL 包含上一轮的改进提示

#### Scenario: 提交回答（面试结束）
- **WHEN** 客户端提交一轮回答且问答已结束
- **THEN** 响应 SHALL 包含状态为「已结束」、总轮次、复盘标识
- **AND** 客户端 SHALL 据此跳转至复盘

#### Scenario: 查询与历史
- **WHEN** 客户端请求会话详情
- **THEN** 响应 SHALL 包含会话状态（含「出题中」态）与对话流水
- **WHEN** 客户端请求历史会话
- **THEN** 响应 SHALL 按用户维度返回历史会话列表，按时间倒序
