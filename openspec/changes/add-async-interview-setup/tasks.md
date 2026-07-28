# Tasks: 模拟面试异步开局

## 1. 后端 create_session 异步化
- [x] 1.1 建 session 时 status=setup_pending（不再 interviewing）
- [x] 1.2 抽出「跑图到第一个 interrupt」为独立后台函数 _run_setup_background(session_id, init)
- [x] 1.3 _run_setup_background 内：新建 db session；执行图到 interrupt → status=interviewing；异常 → status=error
- [x] 1.4 create_session 用 BackgroundTasks 启动 _run_setup_background，立即返回 {session_id, interview_status: "setup_pending"}

## 2. 状态与错误字段
- [x] 2.1 InterviewSessionModel.status 注释补 setup_pending（status 为自由字符串，无需 migration）
- [x] 2.2 error 态用 status="error" + logger 记原因（前端 generic 重试提示，不碰 DB schema）

## 3. getSession 支持出题中态
- [x] 3.1 确认 getSession 在 setup_pending 时返回 status + pending_question=null（天然支持，无需改）
- [x] 3.2 error 态返回 status=error（前端轮询分支处理）

## 4. 前端 Setup：立即跳转
- [x] 4.1 onStart 只取 session_id 跳转，已天然兼容异步（不依赖 first_question）
- [x] 4.2 first_question 异步下为 null，onStart 不读它（无需改）

## 5. 前端 Room：出题中态 + 轮询
- [x] 5.1 onMounted/loadSession：status=setup_pending → 显示「出题中」态 + 启动轮询
- [x] 5.2 轮询 getSession（~3s）→ interviewing 且 pending_question 就绪 → 渲染第一题 + 停轮询
- [x] 5.3 轮询到 status=error → 显示「开局失败 + 重新开始」
- [x] 5.4 超时兜底：轮询达上限（3min）→ 显示失败态（复用 setupError）

## 6. 验证
- [x] 6.1 API 闭环：createSession 0.29s 返回 setup_pending；后台出题完成转 interviewing + 第一题就绪（实测通过）
- [ ] 6.2 错误路径：构造后台出题失败确认前端错误态（逻辑已实现，待手动构造验证）
