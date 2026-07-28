# Spec: 思考过程展示（reasoning-display）

## ADDED Requirements

### Requirement: AI 思考过程增量推送

系统 SHALL 在 LLM 驱动的任务执行期间，向客户端增量推送 AI 的思考过程（reasoning），使客户端能看到 AI 是如何推理的，而非仅看到最终结果。

#### Scenario: 任务执行期间持续推送思考
- **WHEN** 系统执行一个使用推理模型的 LLM 任务
- **THEN** 系统 SHALL 在推理期间持续向客户端下发思考过程的内容片段
- **AND** 思考过程 SHALL 早于或伴随最终结果推送

#### Scenario: 无思考过程时降级
- **WHEN** 底层 LLM 未返回思考过程（非推理模型或接口未暴露）
- **THEN** 系统 SHALL 不下发思考事件
- **AND** 业务结果 SHALL 照常推送（不因缺思考而失败）

---

### Requirement: 思考过程与业务结果分离

系统 SHALL 将思考过程与业务结果作为独立的内容流分别推送，使客户端能在视觉上区分「AI 在思考什么」与「AI 给出的结果」。

#### Scenario: 思考与结果分别下发
- **WHEN** 系统同时产生思考过程与业务结果
- **THEN** 思考过程 SHALL 通过独立的思考事件下发
- **AND** 业务结果 SHALL 通过既有的结果事件下发
- **AND** 客户端 SHALL 能将两者分发到不同的展示区域

#### Scenario: 思考区视觉区别于结果区
- **WHEN** 客户端展示思考过程
- **THEN** 思考区 SHALL 在视觉上区别于业务结果区（如弱化色调、斜体）
- **AND** 思考区 SHALL 支持折叠（应对冗长思考）

---

### Requirement: 简历优化的思考展示

简历优化的简历生成 SHALL 展示 AI 思考过程，且最终简历一次性给出，不再逐字打字机渲染简历正文。

#### Scenario: 生成时展示思考、简历最终一次性出
- **WHEN** 用户触发简历生成
- **THEN** 系统 SHALL 增量推送生成过程中的 AI 思考
- **AND** 系统 SHALL NOT 逐字推送简历正文的生成过程
- **AND** 简历正文 SHALL 在生成完成时一次性下发

---

### Requirement: 简历解析与 JD 匹配的思考展示

简历解析与 JD 匹配 SHALL 在各自的 LLM 环节展示 AI 思考过程。

#### Scenario: 简历解析展示提取思考
- **WHEN** 系统从简历文本提取画像
- **THEN** 系统 SHALL 在提取期间推送 AI 的思考过程

#### Scenario: JD 匹配展示解析思考
- **WHEN** 系统解析 JD 或评估匹配
- **THEN** 系统 SHALL 推送 AI 的思考过程

---

### Requirement: 思考过程期间连接保活

系统 SHALL 在思考过程持续输出期间保持客户端连接活跃，避免因思考耗时长而导致连接超时。

#### Scenario: 思考持续输出不超时
- **WHEN** AI 思考过程持续输出（任务总耗时长）
- **THEN** 系统 SHALL 因持续下发思考片段而保持连接活跃
- **AND** 系统 SHALL NOT 因总时长超过常规请求超时而判定失败
