# Design: 模拟面试异步开局

## 背景

createSession 当前同步：[graph.invoke(init)](backend/src/api/interview.py#L156) 跑 session_setup（出题 ~62s + RAG）到第一个 interrupt，请求阻塞 ~70-85s。
前端 createSession 超时（原 90s，临时 180s）偶发被超 → 「请求失败」。

## 决策

### 决策 1：createSession 立即返回 session_id，出题移到后台

- create_session：建 session（status=setup_pending）→ 启动后台任务跑图 → 立即返回 `{session_id, interview_status: "setup_pending"}`。
- 后台任务跑到 interrupt（第一题就绪）→ session.status = interviewing；失败 → error + 原因。
- 第一题不再由 createSession 返回，改由前端轮询 getSession 拿 pending_question。

**理由**：把慢 LLM 移出 HTTP 请求关键路径，请求 < 1s 返回，彻底消除超时与干等。

### 决策 2：后台任务用 FastAPI BackgroundTasks + 图的异步执行

- 用 FastAPI `BackgroundTasks` 注入；任务函数内执行图到第一个 interrupt。
- 图的执行方式：优先 `graph.ainvoke`（async）；**若当前 SQLite checkpointer 仅同步**，则任务内用 `asyncio.to_thread(graph.invoke, ...)`（线程池跑同步 invoke，不阻塞事件循环）——apply 时实测确认走哪条。
- 任务内**新建独立 db session**（请求 db 随响应关闭），更新 session.status。
- 任务内 try/except：成功 → interviewing；异常 → error + 存 message。

**理由**：BackgroundTasks 是 FastAPI 原生、零额外依赖；to_thread 兜底保证即使 checkpointer 同步也不阻塞。比裸 asyncio.create_task 更可控（框架管理生命周期）。

### 决策 3：前端轮询 getSession（非 SSE）

- 出题就绪是离散事件 + 数据量小（一个 question），轮询（~3s 间隔）简单够用。
- SSE 对单次「完成」事件过度，且要新增 SSE 端点；轮询**复用已有 getSession**（已返回 pending_question）。
- room onMounted：getSession → setup_pending 则显「出题中」+ 轮询 → interviewing 且 pending_question 就绪则渲染 + 停轮询 → error 则提示。

**理由**：最小可行、复用现有 getSession 契约。SSE 留作后续体验增强（与 streaming-pipeline-change 模式统一时再考虑）。

### 决策 4：状态扩展 setup_pending

- InterviewSessionModel.status 新增 `setup_pending`（出题中）。
- 生命周期：`setup_pending`（建会话/出题中）→ `interviewing`（第一题就绪）→ `finished`（结束）；`error` 为异常态。
- getSession 响应携带 status，前端据此分支。

### 决策 5：错误传递——后台失败不表现为「请求失败」

- 后台任务 catch 任何异常 → session.status=error + 可读原因（复用/新增 error 字段）。
- 前端轮询拿到 status=error → 显示「开局失败：<原因> + 重试」，而非泛化「请求失败」。
- 画像缺失仍在 createSession 同步检查（立即返回 PROFILE_MISSING，不进后台）。

### 决策 6：向后兼容

- createSession 响应仍含 session_id；interview_status 由原 interviewing 变 setup_pending（首响应）。
- first_question 字段在异步下为 null（前端不再依赖它，改轮询）。
- submit_answer 不变（用户答题时出题早已完成，status 必为 interviewing）。

## 不做

- 不改出题档位（strong→fast 是方案 2，正交；本变更只做异步化）。
- 不上 SSE（决策 3，留口子）。
- 不改 interrupt/checkpointer 机制与图结构（异步化只改「何时跑图」）。
