# Tasks: 精修简历工作台化

## 1. 锚点装配（HTML 原子标注 Markdown 对应位置）
- [x] 1.1 `resume_exporter.parse_resume_md` 解析时记录每个可编辑片段（bullet / 经历字段 / self-intro 字段 / summary / stack chip）的行号或稳定 id
- [x] 1.2 主题 `render_header / render_entry / render_bullet / render_summary / render_stack`（`tech_dense.py`）为产出的可编辑原子注入 `data-md-line`（或 `data-md-id`）锚点
- [x] 1.3 `assemble_html` 在装配时把解析得到的行号/ id 透传到 render_*，保证原子与 Markdown 片段一一对应
- [x] 1.4 审查函数 `audit` 增补：校验所有可编辑原子都带锚点（漏锚点告警，防回写丢失）

## 2. 手动编辑回写（锚点 patch 当前草稿）
- [x] 2.1 新增 `POST /resume/{id}/patch-draft`：接收 `{patches: [{anchor, text}]}`，定位 checkpointer 当前草稿 MD 对应行做替换，返回新版 MD + 重新装配的 html
- [x] 2.2 patch 应用前校验归属（resume_id 属主）；未命中锚点返回告警列表（不静默丢）
- [x] 2.3 patch 后不落库（仅更新 checkpointer 会话态草稿），与「定稿才落库」一致
- [x] 2.4 单元测试：每种原子（bullet / 经历 org·role·date / self-intro 各字段 / summary / stack chip）编辑后回写正确，未编辑片段原样保留

## 3. 精修流式 + reasoning + 结构化回复
- [x] 3.1 `resume_generator` 新增 `refine_resume_reasoning_stream`（openai client, glm-4.5），yield `(kind, delta)`：reasoning / content，参照 `generate_resume_reasoning_stream`
- [x] 3.2 `get_resume_refine_prompt` 升级：要求输出「自然语言说明 + 改写后简历」，用 `<<<REPLY>>>...<<<RESUME>>>` 分隔；强约束简历段为完整 Markdown
- [x] 3.3 新增 `POST /resume/{id}/refine-stream`（SSE）：**端点直接 orchestrate**（get_state 读 / update_state 写），不 astream graph（见 design 决策 8）
  - reasoning → SSE `reasoning`（思考区打字机）
  - `<<<REPLY>>>` 段 → SSE `token`（自然语言说明一次性下发）
  - `<<<RESUME>>>` 段 → 攒齐，随 `done` 一次性下发新 MD（不打字机）
  - 会话态在 checkpointer（refine 子图）；`done` 携带 reply / resume_md / eval_report / round / resumed
- [x] 3.4 分隔符降级：content 无 `<<<RESUME>>>` 时，全部作 reply、简历沿用上一版，返回提示（`split_reply_resume` 返回 resume_md=None）
- [x] 3.5 旧同步 `POST /resume/{id}/refine` 标记弃用（保留作降级通道，对应流式不可用降级 Requirement）

## 4. 前端工作台重构（左右分栏 + 对话 + 编辑回流）
- [x] 4.1 `views/ResumeRefine.vue` 重构为左右分栏：左侧 `ResumePreview`（编辑态），右侧对话区组件
- [x] 4.2 新增对话区组件 `RefineChat.vue`：消息气泡（用户 / AI）、思考区（灰斜体可折叠）、改写标记、输入框 + 发送 + 定稿按钮
- [x] 4.3 `ResumePreview.vue` 编辑态与父页通信：preview_shell 暴露 `__collectPatches()`，父页**同源直调**（取代 postMessage 异步握手，更简单）；refine 模式隐藏旧 saveBtn（其反序列化逻辑保留作非精修兼容）
- [x] 4.4 `flushEdits()` 不变量：发送 AI 消息 / 定稿前先 `POST /patch-draft` 落当前编辑
- [x] 4.5 AI 回复三层渲染：`onReasoning` → 思考区逐字（打字机）；reply 段 → 气泡（一次性，见 design 决策 8 简化）；resume 段 `onDone` → 左侧 assemble 刷新 iframe
- [x] 4.6 `api/resume.ts` 新增 `refineResumeStream` / `patchDraft`，对接 `openSseStream`
- [x] 4.7 开场白：首条 AI 消息给出操作指引文案（含手改 vs 对话改的边界提示）

## 5. PDF 服务端渲染（Playwright）
- [x] 5.1 后端依赖加 `playwright`；`playwright install chromium`（预编译二进制）
- [x] 5.2 改造 `GET /resume/{id}/pdf`：读最新 MD（会话态优先）→ `assemble_html` + `wrap_preview` → Playwright 渲染 → `application/pdf` 下载（文件名「姓名-岗位」）；前端 exportPdf 内先 flushEdits
- [x] 5.3 渲染失败降级：返回 html + fallback_print，前端提示改用浏览器打印
- [x] 5.4 精确页数：`render_html_to_pdf` 返回 `page_count`（PDF 端点侧兑现精确排版度量）；`estimate_pages` 函数保持粗估（改它会拖慢生成阶段，留后续）
- [x] 5.5 前端「导出 PDF」按钮直接触发下载（fetch blob + Content-Disposition 文件名，不再 `window.print`）

## 6. 测试
- [x] 6.1 锚点 patch 回写单测：各原子编辑后 MD 正确、未编辑片段不变（test_resume_patch.py，同 2.4）
- [x] 6.2 分隔符切分单测：正常 reply/resume 切分、无 `<<<RESUME>>>` 降级、resume 段 Markdown 完整性（test_refine_split.py）
- [x] 6.3 flushEdits 不变量测试：发送/定稿/导出前编辑已落，AI 改写基于含手改的最新草稿（实测：手动编辑 + 对话改混合）
- [x] 6.4 PDF 渲染冒烟：返回合法 PDF、文件名正确、多页分页正常（test_resume_pdf.py）
- [x] 6.5 e2e：生成 → 进入精修 → 手动改 → 对话改（思考+回复+刷新）→ 导出 PDF（实测）

## 7. 验证
- [x] 7.1 手动编辑 + 对话改写混合，左手改不被 AI 改写冲掉（实测）
- [x] 7.2 导出 PDF：真下载（非打印对话框）、含手改、A4 分页（Windows Playwright policy 修复后实测）
- [x] 7.3 思考/回复/简历三层样式区分（灰斜体可折叠 / 气泡 / 左侧刷新）（实测）
- [x] 7.4 降级链路：refine-stream 不可用回退同步 `/refine`（保留）；PDF 渲染失败回退打印（实现就绪，未专门触发实测）
