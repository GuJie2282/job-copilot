# Design: AI 思考过程展示（reasoning）

## 设计原则

1. **建立在流式基础上**：reasoning 复用 add-streaming-pipeline 的 SSE 通道（`openSseStream` / `StreamingResponse`），新增 `reasoning` 事件类型，不另起协议。
2. **思考与结果分离**：reasoning（AI 内部推理）与 content（业务输出）分开发布到不同事件，前端分不同区展示——思考区（灰色/斜体/可折叠）vs 结果区（业务产出）。
3. **真实 reasoning，不伪造**：展示 LLM 真实的 reasoning_content（GLM-4.5 思考 token），不是伪造的进度文案。
4. **横切增强**：reasoning 是三模块共用的能力，抽公共 reasoning stream 服务，各模块按需接入。

---

## 核心设计决策

### 决策 1：reasoning 模型选 glm-4.5（唯一支持 reasoning 的档）

**spike 验证**（2026-07-24，test_reasoning_spike.py / test_reasoning_openai_spike.py）：

| 模型 | reasoning | 说明 |
|---|---|---|
| glm-4.5（strong） | ✅ 有 | reasoning_content 与 content 分离（spike：698 字思考 + 7 字回答） |
| glm-4-flash（fast） | ❌ 无 | 非 reasoning 模型，只有 content |

**结论**：要展示 reasoning，必须用 glm-4.5。三模块相关 LLM 调用 fast → strong。

**代价**：strong 慢（add-streaming-pipeline 实测：分段提取 strong 5 段 >450s 超时）。缓解见决策 7。

### 决策 2：绕过 LangChain，用 openai client 直调

**问题**：LangChain `ChatOpenAI.stream()` 默认只读 `delta.content`，把智谱的 `delta.reasoning_content` **丢了**（spike：LangChain 下 glm-4.5 前 30 chunk content 全空 = 思考阶段，但 reasoning 没进 additional_kwargs / response_metadata）。

**方案**：新增 reasoning stream 服务，用 `openai.OpenAI` / `AsyncOpenAI` 直调智谱兼容接口，显式读 `delta.reasoning_content` + `delta.content`：

```python
async for chunk in client.chat.completions.create(model="glm-4.5", ..., stream=True):
    delta = chunk.choices[0].delta
    if getattr(delta, "reasoning_content", None):
        yield ("reasoning", delta.reasoning_content)
    if delta.content:
        yield ("content", delta.content)
```

**与既有 invoke/stream 版本并存**：`generate_resume` / `generate_resume_stream`（LangChain）保留；新增 `generate_resume_reasoning_stream`（openai client）专供 reasoning 展示。各处按需选用。

### 决策 3：reasoning 与 content 分离推送（SSE reasoning 事件）

**新增 SSE 事件**：

| event | data | 用途 |
|---|---|---|
| `reasoning` | `{delta}` | AI 思考过程 token（新增） |
| `token` | `{delta}` | 业务自由文本 content（简历优化，既有） |
| `segment` | `{section, data}` | 结构化段（画像，既有） |
| `stage/score/done/error` | ... | 既有 |

reasoning 与 content 各自独立事件，前端按事件类型分发到不同回调（`onReasoning` vs `onToken`/`onSegment`）。

### 决策 4：三模块接入点

**简历优化 generate（主战场）**：
- `resume_generate_node` 的 `generate_resume_stream`（LangChain, glm-4-flash）→ `generate_resume_reasoning_stream`（openai client, glm-4.5）
- 节点 `writer` 同时推 reasoning + content 两类 custom event
- 端点 astream custom 解包：reasoning → SSE `reasoning`，content → SSE `token`
- **去掉 content 打字机**（见决策 5）

**简历解析 parse-stream**：
- `profile_extractor._extract_one_section` 的 `llm.stream`（LangChain）→ openai client reasoning stream（glm-4.5）
- 每段提取发 reasoning 事件（段内思考）+ segment 事件（段结果）
- 档位 fast → strong（接受慢，见决策 7）

**JD 匹配 match**：
- JD 结构化解析（`jd_parsing` 节点 / `parse_jd`）→ glm-4.5 reasoning stream
- 发 reasoning 事件（解析 JD 的思考）+ stage/score/done（既有）
- 隐性判断 / 增补建议（`judge_implicit` / `_generate_suggestions`）同样可接 reasoning（增补阶段展示思考）

### 决策 5：简历优化去掉 content 打字机，改 reasoning + 最终一次性出

**现状**（add-streaming-pipeline）：简历优化 generate 有 content 打字机（streamingMd 逐字渲染生成的简历）。

**问题**：用户反馈"简历逐字打字机没意义"（生成的是简历模板，不如看 AI 思考）。

**改造**：
- 移除前端 `streamingMd` ref 与 content 打字机区
- 改为：**reasoning 区**（AI 思考过程逐字，灰色斜体）+ **简历最终结果由 `done` 一次性给出**（content_md 整体渲染，不打字机）
- content token（SSE `token` 事件）后端仍可推（保活），但前端**不逐字渲染**，只在 done 时落完整简历

> 简历优化的 reasoning 是最有价值的展示（AI 如何根据画像+岗位组织简历、强调什么）。

### 决策 6：前端 reasoning 区（公共、灰色斜体、可折叠）

三模块共用一个"AI 思考中"区样式：
- 灰色 / 斜体 / 区别于业务结果区
- 可折叠（reasoning 可能冗长，用户可收起）
- 打字机逐字（onReasoning 追加）

实现：`onReasoning` 回调把 delta 追加到 `reasoningText` ref，模板渲染（灰色斜体 pre / 可折叠 details）。

### 决策 7：strong 慢的缓解

strong（glm-4.5）+ reasoning 双段（思考 + 回答）比 fast 单段慢得多。缓解：

1. **流式保活**：reasoning token 持续输出，连接活跃，不超时（add-streaming-pipeline 已验证）
2. **reasoning 让等待有内容**：用户看 AI 思考，不枯燥（相比 fast 干等）
3. **接受长耗时**：用户选"三模块都接"即接受变慢；reasoning 展示补偿体验
4. **可折叠**：reasoning 冗长可收起

---

## 架构

```
┌──────────────── 前端 ────────────────┐
│  ResumeParser / ResumeOptimizer / JdMatcher
│    onReasoning → reasoningText（思考区，灰色斜体可折叠）
│    onSegment/onToken/onDone → 业务结果区（既有）
│  src/utils/sse.ts 加 onReasoning
└──────────────────┬───────────────────┘
                   │ SSE: reasoning / token / segment / done
                   ▼
┌──────────────── 后端 ────────────────┐
│  StreamingResponse + sse("reasoning", {delta})  （src/core/sse.py 加 REASONING 常量）
│        │
│   ┌────┴──────────────────────┐
│   ▼                           ▼
│ 简历优化 generate          简历解析 parse-stream / JD match
│  generate_resume_reasoning   _extract_one_section / parse_jd
│  _stream（openai client）    改 openai client reasoning stream
│        │                           │
│   ┌────┴────────────────────────────┴────┐
│   ▼  src/services/llm_reasoning.py（新增公共层）
│   async def stream_chat_with_reasoning(prompt, ...) -> yields ("reasoning"|"content", delta)
│   用 AsyncOpenAI 直调智谱 GLM-4.5，读 delta.reasoning_content + delta.content
└──────────────────────────────────────────┘
```

---

## 与 add-streaming-pipeline 的关系

- **依赖**：本变更建立在 add-streaming-pipeline 的流式通道（`openSseStream` / `StreamingResponse` / `sse()`）上，复用而非另建。
- **并行**：add-streaming-pipeline 尚有 refine 流式（Phase 8）+ 区块五测试未完成；本变更独立推进，互不阻塞。
- **模型档位冲突**：add-streaming-pipeline 把简历解析分段提取改 fast（避超时）；本变更又改回 strong（接 reasoning）。**以本变更为准**（用户选"三模块都接 reasoning"，接受 strong 慢 + 靠流式保活）。

## 风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| strong + reasoning 双段慢 | 三模块耗时长 | 流式保活防超时 + reasoning 让等待有内容 + 可折叠 |
| reasoning 冗长 | 体验啰嗦 | 前端 reasoning 区可折叠/限高 |
| openai client 直调绕 LangChain | 失去 LangChain 重试/容错 | reasoning stream 服务自带重试；失败降级（不发 reasoning，只发 content） |
| 智谱 reasoning_content API 变动 | reasoning 拿不到 | 降级：reasoning 空，退化为纯 content 流式（add-streaming-pipeline 状态） |

## 面试讲解要点

1. **reasoning 透明化的产品价值**：从黑盒结果到可解释推理，信任感 + 发现 AI 错误——产品思维。
2. **技术深度：绕 LangChain 拿 reasoning_content**：spike 发现 LangChain 丢 reasoning，用 openai client 直调——体现"不盲信框架、能钻到协议层"。
3. **分层选模权衡**：reasoning 要 strong（慢），业务速度要 fast——按场景选档，明确取舍。
4. **思考与结果分离的架构**：不同 SSE 事件 + 前端分区，reasoning 是横切增强，三模块复用。
