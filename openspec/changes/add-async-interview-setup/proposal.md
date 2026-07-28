# Proposal: 模拟面试异步开局（add-async-interview-setup）

## Why

创建面试会话时，session_setup 要调 strong 档（glm-4.5）出题，实测单次 ~62s + RAG 检索，总 ~70-85s。
当前 createSession 在 HTTP 请求内**同步**跑出题，前端必须阻塞等待 → 偶发超过前端超时（原 90s，已临时放宽到 180s）报「请求失败」；
即便不超时，用户在「开始面试」按钮上干等 60-85s，体验差。

根因不在出题质量，而在**「慢 LLM 阻塞 HTTP 请求」**。把开局异步化：createSession 立即返回 session_id，
后台出题，前端进入面试间后轮询直到第一题就绪。用户点「开始面试」瞬间跳转、看到「出题中」反馈，不再卡死或超时。

> 与 evolve-interview-pacing 无关（那是评估/决策的节奏改造，本变更只改「何时跑出题」，不改出题内容/图结构）。
> 与出题降档（strong→fast）正交，二者可叠加，但分开立项（本变更只做异步化）。

## What Changes

- createSession 改为异步：建 session（status=setup_pending）→ 启动后台任务跑图出题 → 立即返回 session_id（不含第一题）。
- 后台任务跑到第一个 interrupt（第一题就绪）后，把 session.status 置为 interviewing；出题失败置 error 并存原因。
- 新增会话状态 setup_pending（出题中）。
- 前端：onStart 拿到 session_id 立即跳面试间；面试间 onMounted 轮询 getSession，直到 status=interviewing 且 pending_question 就绪后渲染第一题；setup_pending 期间显示「出题中」加载态。
- 错误传递：后台出题失败时，前端轮询拿到 error 态并提示，不再表现为泛化「请求失败」。

## Capabilities

- `mock-interview`（ADDED）：异步开局——创建请求立即返回、后台出题、轮询获取第一题、setup_pending 状态与错误传递。

## Impact

- **改动文件**：`api/interview.py`（create_session 异步化 + 后台任务）、`views/InterviewSetup.vue`（onStart 不等第一题）、`views/InterviewRoom.vue`（onMounted 轮询 + 出题中态）、`models/interview.py`（status 注释补 setup_pending）。
- **不动**：出题逻辑（question_generator）、interrupt/checkpointer 机制、submit_answer、evaluator/护栏（evolve）、复盘。
- **风险**：后台任务生命周期与错误处理（db session 需在任务内新建）；SQLite checkpointer 的 async 支持（若仅同步，后台任务用 run_in_executor 跑同步 invoke）；轮询频率与及时性权衡。
- **面试讲点**：把「慢 LLM 阻塞请求」的同步架构，演进为「立即响应 + 后台处理 + 轮询」的异步架构，体现对 LLM 延迟与 Web 请求模型的工程理解。
