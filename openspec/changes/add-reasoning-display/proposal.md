# Proposal: AI 思考过程展示（reasoning）

## Why（为什么需要）

### 当前痛点
流式管线（add-streaming-pipeline）让用户看到「任务进度」与「最终结果」（画像逐段成型、简历生成、评分秒出），但**看不到 AI 是如何思考的**——用户只看到"提取基本信息…"的进度文案，却不知道 AI 在分析什么、为什么这么提取/生成。结果是黑盒输出，用户难以建立信任、也难以发现 AI 的误判。

### 产品价值
**思考过程（reasoning）展示**把 AI 的内部推理透明化：

1. **信任感与可解释性**：用户看到"AI 在分析这段经历的 STAR 结构…候选人项目强调数据成果…"，理解为什么得出这个画像/简历/评分——从"黑盒结果"变成"可解释推理"。
2. **差异化与面试讲点**：reasoning 展示是前沿 AI 产品的体验（DeepSeek-R1 / Claude thinking）。求职 Copilot 作为 AI 作品集项目，这是有技术深度 + 产品思维的讲点。
3. **发现 AI 错误**：用户能从思考过程发现 AI 的误判（如错误关联经历），及时纠正，而不是对着错误结果发呆。

### 战略定位
建立在 add-streaming-pipeline 的流式基础上的体验增强：流式管线下发 reasoning token，前端"AI 思考中"区逐字展示，与业务输出（画像/简历/评分）分离呈现。

## What Changes（做什么变更）

### 新增能力
1. **reasoning-display（思考过程展示）**
   - 三条核心链路（简历解析 / 简历优化 / JD 匹配）的 LLM 调用展示 reasoning
   - reasoning 与业务输出分离：前端"AI 思考中"区（灰色/斜体）逐字展示思考，业务结果区照常
   - 连接保活：reasoning token 持续下发，连接活跃（兼顾 add-streaming-pipeline 的超时治理）

### 系统变更
- **LLM 调用层**：新增 reasoning stream 服务，用 openai client 直调智谱 GLM-4.5，读 `delta.reasoning_content`（LangChain ChatOpenAI 默认丢 reasoning_content，必须绕过——见 design 决策 2）
- **模型档位**：三模块相关 LLM 调用 glm-4-flash → **glm-4.5**（strong，当前唯一支持 reasoning 的档）
- **SSE 协议**：新增 `reasoning` 事件（{delta}），与既有 stage/segment/token/done 并列
- **前端**：公共 `SseHandlers` 加 `onReasoning`；各模块加"AI 思考中"区（reasoning 打字机）
- **简历优化**：移除当前的"简历内容打字机"（streamingMd），改展示 reasoning；简历最终结果由 done 一次性给出

## Capabilities（能力清单）

### reasoning-display（思考过程展示）
**能力描述**：在 LLM 驱动的任务中，向客户端增量推送 AI 的思考过程（reasoning），与业务输出分离展示。

**核心行为**：
```
LLM 调用（glm-4.5 reasoning 模型，openai client 直调）
  → reasoning token 增量推送（event: reasoning）
  → content / 业务结果照常推送（event: token / segment / done）
  → 前端：思考区逐字展示 reasoning + 业务结果区展示最终输出
```

**适用**：简历优化（生成）、简历解析（提取）、JD 匹配（解析/评估）。

## Impact（影响分析）

### 用户体验影响
**正面**：
- AI 思考透明化，信任感 + 可解释性提升
- reasoning 持续输出，等待时有内容看（不枯燥）

**风险**：
- glm-4.5（strong）慢，三模块变慢（简历解析分段 strong 前面超时过）→ 缓解：流式保活防超时；reasoning 本身让"等待时有内容"
- reasoning 可能冗长 → 缓解：前端 reasoning 区可折叠/限高

### 技术影响
**依赖**：建立在 add-streaming-pipeline 的流式基础（SSE 通道、openSseStream）之上。
**新增**：openai client 直调层（绕 LangChain 拿 reasoning_content）。
**架构**：reasoning 是横切增强，复用三模块现有流式通道，新增 reasoning 事件类型。

### 开发影响
**工作量**：
- 公共 reasoning stream 服务 + SSE reasoning 事件：1 天
- 三模块接入（简历优化去打字机 + 简历解析分段 + JD 解析）：2-3 天
- 前端 reasoning 区（三模块）：1 天
- 测试打磨：1 天
- **总计：5-6 天**

**技术风险**：
- glm-4.5 reasoning 冗长 → 缓解：reasoning 区可折叠
- strong 慢 → 缓解：流式保活 + reasoning 持续输出

## Success Criteria（成功标准）

- [ ] 简历优化 generate：展示 AI 思考过程（reasoning 打字机），简历最终一次性出（去掉原 content 打字机）
- [ ] 简历解析：分段提取展示思考过程
- [ ] JD 匹配：JD 解析/评估展示思考过程
- [ ] reasoning 与业务输出视觉分离（思考区灰色/斜体/可折叠）
- [ ] reasoning 持续输出期间连接活跃（不超时）

## Timeline（时间线）

**阶段 1：公共 reasoning 基础（Day 1，1 天）**
- openai client 直调 reasoning stream 服务（yield reasoning + content）
- SSE reasoning 事件 + 前端 onReasoning

**阶段 2：简历优化（Day 2，1 天）**
- generate 改 glm-4.5 reasoning stream
- 去掉 content 打字机，改 reasoning 区 + 简历最终

**阶段 3：简历解析 + JD 匹配（Day 3-4，2 天）**
- 分段提取改 glm-4.5 reasoning stream
- JD 解析改 glm-4.5 reasoning stream

**阶段 4：测试打磨（Day 5，1 天）**
- 三模块 reasoning 展示、可折叠、降级

**总计：约 5 天**
