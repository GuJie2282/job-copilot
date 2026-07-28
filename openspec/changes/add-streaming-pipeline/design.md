# Design: 长耗时 LLM 任务的流式管线

## 设计原则

1. **统一模式，按需选粒度**：所有长耗时 LLM 任务走同一条流式通道，但根据"输出性质"选择最合适的推送粒度（token / 段 / 阶段），不为统一而强行套用同一粒度。
2. **复用先例**：JD 匹配已落地"阶段级 SSE"（`graph.astream` + `StreamingResponse` + 前端 fetch 流式），本变更将其公共化并按输出性质扩展到 token 级与段级，不另起炉灶。
3. **流式与质量合流**：简历解析借流式改造之机，把"一次提取整份画像"重构为"分段提取"，一次改造同时解决超时与字段错位两类问题。
4. **保活为体，进度为用**：流式的底层价值是"连接保活消除超时墙"，上层价值是"真实进度反馈"；两者由同一套事件机制承载。
5. **可降级、可恢复**：任意阶段失败不影响已产出结果，连接中断后已落库的部分结果可被读取或续作。

---

## 核心设计决策

### 决策 1：流式协议选型 —— SSE over HTTP

**候选**：SSE（Server-Sent Events）/ WebSocket / 长轮询。

**最终选择**：**SSE over HTTP**（`text/event-stream`）。

**理由**：
- 任务交互是**单向**的（服务端 → 客户端推送进度与结果），客户端只在发起与取消时需要信令，HTTP 请求体 + AbortController 已足够，不需要 WebSocket 的双向通道。
- SSE 走标准 HTTP，复用现有鉴权（Authorization 头）、CORS、路由，无需额外的连接层与状态机。
- 浏览器原生支持自动重连与事件解析语义；本项目用 POST（请求体长）+ 鉴权头，改用 fetch 手写解析（见决策 3），仍属 SSE 协议。
- 长轮询无法解决"任务执行期间的单次请求超时"，且实现啰嗦，排除。

**权衡**：SSE 是单工（服务端→客户端），客户端取消靠关闭连接（fetch AbortController），不如 WebSocket 的双向信令优雅，但单向推送场景下这点代价可忽略。

### 决策 2：按输出性质分配流式粒度（核心架构决策）

不同任务的"输出"性质不同，决定了最优的推送粒度。强行统一粒度会要么"卡顿"（结构化输出半截无法渲染）要么"浪费"（自由文本不必等整段）。

| 任务 | 输出性质 | 推送粒度 | 理由 |
|---|---|---|---|
| 简历优化（生成/精修） | Markdown 自由文本 | **token 级** | 自由文本可逐字渲染，打字机效果体验最佳；首字节时间大幅提前 |
| 简历解析（提取画像） | 结构化 JSON | **段级** | 半截 JSON 无法解析渲染；按"基本信息/教育/工作/项目/技能"分段，每段整段完成后下发 |
| JD 增补（Gap） | 结构化 JSON | **阶段级** | 半截 JSON 无法渲染；按"隐性判断/建议生成"阶段完成下发 |

> 这是对 add-jd-matching 决策 9（"token 级留给自由文本场景"）的延展：JD 评分链当时选阶段级、明确把 token 级留给自由文本；本变更新增的两类自由文本任务（简历生成/精修）正好承接 token 级，结构化任务（画像/Gap）承接段级与阶段级。

**粒度选择规则（写入公共工具文档，供后续任务复用）**：
- 输出可"边产生边有意义地渲染" → token 级
- 输出可"按自然分段整体渲染" → 段级
- 输出只能"整段完成才有意义" → 阶段级

### 决策 3：客户端消费方式 —— fetch + ReadableStream 手写解析

**最终选择**：原生 `fetch` + `ReadableStream` 手写 SSE 事件解析（零依赖）。

**理由**：
- 任务端点是 **POST**（请求体携带简历/JD 长文本、画像数据），浏览器原生 `EventSource` **仅支持 GET**，不可用。
- 需要携带 `Authorization` 鉴权头，`EventSource` 对自定义头支持差。
- JD 匹配已实现并验证此模式（按 `\n\n` 切事件块、解析 `event:`/`data:` 行、JSON.parse data），本变更抽取为公共工具复用。
- 取消语义清晰：`AbortController.abort()` 关闭 fetch 即终止任务。

### 决策 4：连接保活与超时模型

流式改造要消除的是**两层超时**，必须同时处理：

- **HTTP 层超时**（前端请求超时、代理 idle、浏览器 idle）：由"持续推送事件 + 空闲心跳"消除。任务执行期间若某段无内容可推（如单段 LLM 仍在生成但该段为结构化、未到整段下发时机），定期下发 SSE 注释（`: keepalive`）保活。
- **LLM 层超时**（LLM 自身单次调用超时）：由"增量输出"消除。`stream` 模式下，token 持续到达，超时语义从"整次调用总时长"变为"两个 chunk 之间的间隔"，长输出不再因总时长超时被切断。

> 关键认知：**只包一层 SSE 发心跳、底层仍是同步 invoke，救不了 LLM 自身超时**——因为 LLM 阻塞期间 SSE 通道无内容可发。因此结构化任务（段级）的每一段 LLM 调用也采用增量输出，确保段内连接活跃；自由文本任务（token 级）天然活跃。

**前端超时策略调整**：流式端点不再设置"覆盖全流程"的大超时（如原 180s/300s），改为依赖流式保活 + 一个宽松的"连接级超时"（仅在没有收到任何数据时触发，收到首字节后由数据流维持）。

### 决策 5：简历解析分段提取（结构 + 流式）

**现状问题**：
- 一次 LLM 调用提取整份画像（扁平平行数组 schema），长简历下：① 单次耗时长易超时；② 平行数组（`project_names[]`/`project_roles[]`/`project_descriptions[]`）靠下标对齐，错位导致"项目名张冠李戴"。

**重构方案**：拆分为按段的多次小 LLM 调用。

```
段 1：基本信息（姓名/电话/邮箱/地点/个人总结）
段 2：教育背景（数组）
段 3：工作/实习经历（数组，含详情）
段 4：项目经验（数组，含详情）
段 5：技能 + 荣誉 + 求职目标
```

**每段**：
- 独立的、聚焦的 prompt（只提取该类信息 + 对应原文），上下文窄、输出短、准确率高。
- 采用增量输出（stream），段内连接活跃。
- 段完成后整段下发 `segment` 事件（该段的结构化结果 + 该段置信度），前端可立即渲染该段（画像逐段成型）。
- 段间下发 `stage` 进度事件。
- 全部段完成后下发 `done`（完整画像 + 完整置信度 + 质量分）。

**容错**：某段失败只重试该段（不影响已成功的段），重试耗尽则该段置空并在 `done` 中标注，不拖垮整份画像。

**置信度衔接**：现有 `calculate_profile_confidence` 按字段路径遍历计算，与分段提取天然兼容——每段结果可直接计算该段置信度，最终合并为完整置信度字典。

> 分段提取是"超时"与"质量"的合流点：单段小而快（治超时）、上下文聚焦（治漏提取）、配合嵌套结构（治错位），一次重构解决三类问题。

### 决策 6：画像结构嵌套化

**调整**：`工作经历` / `项目经验` / `教育背景` 由"多个平行数组靠下标对齐"改为"对象数组"。

```
调整前（扁平平行数组，易错位）：        调整后（嵌套对象数组，字段绑死）：
companies: [A, B]                      work_experience: [
positions: [p1, p2]                      {company:A, position:p1, duration:.., description:..},
durations: [d1, d2]                      {company:B, position:p2, duration:.., description:..}
work_descriptions: [w1, w2]            ]
```

**理由**：对象的字段在结构上绑死，LLM 无法把 A 的描述错挂到 B。这是对"项目名错位"问题的结构性根治，与分段提取（决策 5）协同——每段本就是提取一组对象。

**前端联动**：`ProfileDisplay` / `ProfileEditor` 由"按下标拼平行数组"改为"遍历对象数组"，展示与编辑逻辑随之简化。结构变更与流式改造在同一变更内同步完成，避免中间态。

**兼容**：画像持久化（`detail_json`）是无损 JSON 列，结构调整不影响存储层；历史画像若存在旧结构，读取时做一次性迁移适配。

### 决策 7：简历优化 token 级输出

**适用**：路径 A 生成（`resume_generate`）、路径 B 改写（`refine`）——均输出 Markdown 自由文本。

**方案**：服务层生成函数由 `llm.invoke(prompt)` 一次性返回，改为 `llm.stream(prompt)` 增量产出 token；图节点改为聚合 token 并通过流式通道以 `token` 事件逐个下发，前端拼接呈现打字机效果。

**与阶段进度的关系**：token 级（生成内容逐字）与阶段级（节点完成）并存——`resume_generate` 节点执行期间持续发 `token`，节点完成后发 `stage`（"生成完成，进入评估"）。评估、校验、导出等非自由文本节点仍走阶段级。

**LLM 档位**：简历优化现用 fast 档（glm-4-flash），多轮迭代靠串行累积。流式不改变档位选择，但 token 级让用户在首字节后即见生成，体感耗时大幅下降；同时 stream 模式缓解单次生成因输出长而接近超时的风险。

**增量 Markdown 渲染**：前端边收 token 边追加到 Markdown 渲染区；因 Markdown 在不完整时仍可部分渲染，无需等全部 token。

### 决策 8：简历优化路径 B（interrupt + 流式）

**现状**：路径 B 精修用 LangGraph `interrupt` + SqliteSaver checkpointer，跨请求维持状态（首次加载草稿与评估 → 用户给反馈 → 改写+重评估 → 定稿）。

**流式方案**：
- 每轮 `/refine` 请求内部仍是"单次图执行（跑到下一个 interrupt）"，但这次执行改为 `astream`：改写节点 token 级输出、评估节点阶段级。
- `interrupt` 暂停语义与流式不冲突：astream 在 interrupt 处自然停止，前端收到当前轮结果后等待用户下一轮反馈。
- `/finalize` 不涉及 LLM（纯校验+导出+落库），保持同步快速返回，不流式。

**权衡**：路径 B 每轮 LLM 少（2 次）、单轮耗时短，流式收益小于路径 A；但 token 级改写输出体验提升仍值得做，且与路径 A 共用同一套生成流式实现。

### 决策 9：JD 增补并入匹配主流

**现状**：`/match` 流式到 `done`（分数 + 规则 Gap 骨架）即关流；Gap 增补（`enrich_gaps`：隐性偏好判断 + 建议生成，两段主力档 LLM）是独立同步端点，60 秒超时。

**方案**：`/match` 的 `done`（评分完成）后**不关流**，继续执行增补并以事件推送：
```
... score（分数）→ done（评分完成 + 骨架）   ← 现有，改为不关流
  → stage "正在分析隐性偏好…"
  → stage "正在生成应对建议…"
  → enriched（最终 Gap 清单，含隐性判断 + 建议）  ← 新增，真正关流
```

**理由**：用户提交一次 JD 即可看到"评分 → 增补"全流程，无需再触发独立的增补请求；增补内部两段 LLM 也采用增量输出避免段内超时。增补失败的降级不变（模板建议 / 隐性 partial），失败时发 `error` 或在 `enriched` 中标注降级项。

**持久化**：评分链已前移持久化（`result_id` 在 score 时已存在），增补完成后 UPDATE 同一行的 `gaps_json`，与现状一致。

### 决策 10：LLM 增量调用与超时/重试策略

**增量调用**：LangChain `ChatOpenAI` 原生支持 `.stream()`，返回 token 迭代器。服务层新增"增量生成"路径，与既有 `invoke` 并存，按任务性质选用（自由文本/段内结构化用 stream，纯规则步骤不调 LLM）。

**超时语义**：stream 模式下，LLM 超时从"整次调用总时长"转为"chunk 间隔"，长输出不再因总时长切断。流式端点单次 LLM 调用的 timeout 仍保留（防 LLM 卡死无响应），但因 token 持续流，正常情况下不会触发。

**重试策略调整**：
- 结构化任务的段级提取：失败只重试当前段，不波及全流程；超时类错误重试意义有限（线性叠加耗时），重试次数收敛。
- 自由文本任务的 token 级生成：流中断后重试需整段重来（无法从中间续传），重试次数保守。
- 既有指数退避机制保留。

### 决策 11：错误处理与降级

**错误事件**：任意阶段失败，下发 `error` 事件（含错误码 + 用户可读文案）后关闭流。错误码沿用并扩展现有约定（如 `PARSE_FAILED` / `LLM_FAILED` / `PROFILE_MISSING`）。

**部分结果保留**：
- 简历解析：已成功的段在前端已渲染，`error` 后这些段仍可见；已落库的画像可被后续读取。
- 简历优化：已生成的草稿若已落库（路径 A 在 `resume_persist` 落库），中断后可从草稿续作（路径 B 精修）。
- JD 匹配：评分已落库，增补失败时分数与骨架 Gap 仍可用。

**降级**：
- LLM 失败：结构化任务该段置空标注、自由文本任务提示重试；JD 增补降级为模板建议。
- 流式不可用（如代理拦截 text/event-stream）：端点探测到不支持时，回退为同步 JSON 响应（兼容模式），前端按同步逻辑处理。

### 决策 12：公共流式基础设施抽取

**现状**：SSE 事件组装（`_sse`）内联在 `jd.py`；SSE 消费（fetch + 解析 + dispatch）内联在 `jd.ts`。仅 JD 模块可用。

**抽取**：
- 后端 `src/core/sse.py`：`sse(event, data)` 事件组装 + 常用事件常量（stage/segment/token/done/error）+ 心跳（`sse_keepalive()`）。
- 前端 `src/utils/sse.ts`：`openSseStream(url, body, handlers, token)` 封装 fetch + ReadableStream 解析 + 事件分发 + AbortController，返回取消函数；`handlers` 按 event 类型回调。
- 三模块（简历解析 / 简历优化 / JD）共用，JD 既有实现迁移至公共工具。

**开发环境直连**：vite 开发代理不转发 `text/event-stream`（JD 已踩坑）。前端流式请求用独立的 `VITE_STREAM_BASE_URL` 直连后端，绕开代理；未配置时回退到普通 API base（流式可能不工作但不报错，便于降级）。

---

## 架构设计

### 系统架构图

```
┌──────────────────── 前端（Vue 3）────────────────────┐
│                                                       │
│  ResumeParser / ResumeOptimizer / JdMatcher           │
│        │ openSseStream(url, body, {                   │
│        │     onStage, onSegment, onToken,             │
│        │     onDone, onError })                       │
│        ▼                                               │
│  src/utils/sse.ts  ← 公共：fetch + ReadableStream     │
│  (POST + Authorization + AbortController)             │
│  直连 VITE_STREAM_BASE_URL（绕开 dev proxy）          │
└────────────────────────┬──────────────────────────────┘
                         │ text/event-stream
                         ▼
┌──────────────────── 后端（FastAPI）──────────────────┐
│                                                       │
│  StreamingResponse(event_stream())                   │
│        │                                             │
│        ▼                                             │
│  src/core/sse.py  ← 公共：sse() / sse_keepalive()    │
│        │                                             │
│   ┌────┴─────────────────┬──────────────────────┐    │
│   ▼                      ▼                      ▼    │
│ 简历解析              简历优化                JD匹配  │
│ (段级 segment)      (token 级 + 阶段)       (阶段+并入)│
│ 分段提取              astream 节点流          astream │
│ 每段 llm.stream       生成节点 llm.stream     增补并入│
│   │                      │                      │    │
│   └────────┬─────────────┴──────────────────────┘    │
│            ▼                                         │
│     LangGraph astream / llm.stream（增量）           │
└──────────────────────────────────────────────────────┘
```

### 事件协议（text/event-stream）

统一事件类型，三模块共用：

| event | data 字段 | 用途 | 用于 |
|---|---|---|---|
| `stage` | `{message, node?}` | 阶段进度 | 全部 |
| `segment` | `{section, data, confidence?}` | 分段结构化中间结果 | 简历解析 |
| `token` | `{delta}` | 增量自由文本 | 简历优化（生成/改写） |
| `score` | `{overall_score, dimension_scores, level, ...}` | 评分 | JD 匹配（既有） |
| `done` | 最终结果 | 任务完成 | 全部 |
| `enriched` | `{gaps}` | 增补完成 | JD 匹配（新增） |
| `error` | `{error_code, error_message}` | 失败 | 全部 |
| （注释） | `: keepalive` | 空闲保活 | 全部 |

> `score` 是 JD 匹配既有事件，保留；其余为本变更新增/统一。

### 三模块数据流

**简历解析（段级）**：
```
POST /api/resume/parse-stream
  stage "正在解析 PDF…" → stage "文本质量检测…"
  → stage "提取基本信息…"   → segment {section:"basic", data:{...}}
  → stage "提取教育背景…"   → segment {section:"education", data:[...]}
  → stage "提取工作经历…"   → segment {section:"work", data:[...]}
  → stage "提取项目经验…"   → segment {section:"project", data:[...]}
  → stage "提取技能荣誉…"   → segment {section:"skills", data:{...}}
  → done {profile, confidence, quality_score}
  （任一段失败 → error，已下发段保留）
```

**简历优化（token + 阶段）**：
```
POST /api/resume/generate
  stage "准备画像与岗位…"
  → stage "生成简历草稿…" → token {delta} × N（打字机）
  → stage "六维评估中…"   → （评估节点阶段级）
  → [若不通过，回生成] stage "根据评估优化…" → token × N
  → stage "校验/导出…"    → done {resume_id, content_md, html, eval_report}
```

**JD 匹配（阶段 + 增补并入）**：
```
POST /api/jd/match
  stage "解析 JD…" → stage "加载画像…" → stage "比对匹配度…"
  → score {overall_score, dimension_scores, ...}
  → done {result_id, job_profile, gaps（骨架）}        ← 既有，不再关流
  → stage "分析隐性偏好…" → stage "生成应对建议…"
  → enriched {gaps（含隐性判断 + 建议）}                ← 新增，关流
```

---

## 与现有实现的集成

- **JD 匹配**：`/match` 现有 `event_stream()` 扩展（`done` 后继续增补）；`_sse` / 前端 `matchJd` 迁移至公共工具，行为不变。
- **简历解析**：既有同步 `parse-file`/`parse-text` 保留（兼容/降级），新增 `parse-stream`；提取逻辑从 `get_json_extraction_prompt`（单次）重构为分段 prompt 集合。
- **简历优化**：`generate` 由 `graph.invoke` 改 `graph.astream`；生成服务 `generate_resume` / `refine_resume` 增加增量版本；前端 `ResumeOptimizer.vue` 假进度替换为真实 `onStage`/`onToken` 回调。
- **画像结构**：`UserProfile` 嵌套化，`ProfileDisplay`/`ProfileEditor` 适配，`calculate_profile_confidence` 不变（兼容嵌套）。
- **公共工具**：`src/core/sse.py`、`src/utils/sse.ts` 新增；`.env.development` 增 `VITE_STREAM_BASE_URL`。

## 风险与缓解

| 风险 | 影响 | 概率 | 缓解 |
|---|---|---|---|
| 增量 JSON 无法边收边渲染 | 段级/token 级渲染错乱 | 中 | 结构化任务按段整体下发（决策 2/5）；仅自由文本用 token |
| 流式与 interrupt 结合的暂停语义 | 路径 B 状态错乱 | 中 | 路径 B 单独设计，astream 在 interrupt 自然停（决策 8） |
| 画像结构变更的前后端中间态 | 展示/编辑异常 | 中 | 结构与流式同变更同步落地；历史画像读取迁移适配（决策 6） |
| 开发代理不转发流式 | 本地流式失效 | 高（已知） | 流式端点直连后端（决策 12），JD 已验证 |
| 段级提取总 LLM 次数增多 | 端到端总耗时略增 | 中 | 单段更快更准，换取准确率与体验；段可并行优化留后续 |
| 流式中断后部分结果丢失 | 用户需重来 | 低 | 部分结果前端可见 + 已落库可续作（决策 11） |

## 技术选型总结

| 维度 | 选型 | 理由 |
|---|---|---|
| 流式协议 | SSE（text/event-stream） | 单向推送、HTTP 兼容、复用鉴权（决策 1） |
| 客户端消费 | fetch + ReadableStream 手写解析 | POST + 鉴权头，EventSource 不适用（决策 3） |
| 推送粒度 | token / 段 / 阶段（按输出性质） | 各得其所，避免强行统一（决策 2） |
| 保活 | 事件流 + 空闲心跳 | 消除 HTTP 层超时（决策 4） |
| LLM 调用 | stream（增量）与 invoke 并存 | 消除 LLM 层超时 + 打字机体验（决策 7/10） |
| 编排 | LangGraph astream | 复用图编排，节点级进度天然（决策 7/8/9） |
| 公共化 | 后端 sse 工具 + 前端 sse 封装 | 三模块共用，避免重复（决策 12） |

## 面试讲解要点

1. **"SSE 不是银弹"的工程深度**：能区分 HTTP 层超时（前端/代理 idle）与 LLM 层超时（SDK 自身），讲清"只包 SSE 发心跳、底层仍同步 invoke，救不了 LLM 超时"，必须配合 stream。这是区分"会用流式"与"懂流式"的关键。
2. **按输出性质分配粒度**：不强行统一，结构化输出按段、自由文本按 token，体现"以数据形态驱动架构"的判断力。
3. **流式与质量合流**：借流式改造把简历解析重构为分段提取，一次改动同时治超时与字段错位，体现"用一次成本解决多类问题"的产品工程思维。
4. **协议选型权衡**：SSE vs WebSocket vs 轮询，单向推送场景下 SSE 的代价最小；POST + 鉴权为何放弃 EventSource 改手写 fetch。
5. **可降级可恢复**：流式中断不丢部分结果、结构变更无中间态，体现对用户体验与数据一致性的兼顾。
