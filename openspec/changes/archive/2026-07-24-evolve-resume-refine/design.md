# Design: 精修简历工作台化（evolve-resume-refine）

## 设计原则

1. **真相源单一**：Markdown 是简历的唯一真相源，HTML 永远是它的程序化派生渲染。手动编辑与 AI 改写都读写同一份 Markdown，绝不出现「HTML 一份、Markdown 一份」的双源真相。
2. **复用而非重造**：预览壳已内置 contenteditable 编辑能力，复用它做左侧编辑器，不重写编辑层；精修子图已用 interrupt + checkpointer 范式，对话式只改交互外壳，不动会话内核。
3. **局部回写，不重建整份**：用户的手动编辑只回写到对应 Markdown 片段，其余原封不动——避免「全量 HTML→MD 反序列化」丢字段、错结构的老问题。
4. **思考与结果分离**：沿用 add-reasoning-display 的「reasoning / content 分离推送 + 前端分区」范式，把它从生成阶段延伸到精修。
5. **简单优先**：对话式不升级成 ReAct agent，仍是 interrupt 多态；结构化输出用轻量分隔符而非 JSON 流式解析。

---

## 核心设计决策

### 决策 1：Markdown 为唯一真相源，HTML 是派生

**事实**：`resume_exporter` 把 Markdown 程序化装配成 HTML（`assemble_html` 套主题组件原子 → `wrap_preview` 注入预览壳）。HTML 的每个组件原子（Header / SectionHead / Stack / Entry / Bullet / Summary）都对应 Markdown 里确定的一段。

**推论**：用户「在 HTML 上改文字」改的是派生产物。若放任 HTML 成为第二真相源，AI 下次改写仍读旧 Markdown，用户的手改就会丢。因此必须保证：**HTML 编辑能精确回流到 Markdown，且 AI 改写读的是回流后的最新 Markdown。**

**面试讲点**：这是「所见即所得编辑」与「AI 改写」结合时最容易踩的双源真相坑。很多产品让用户在富文本里改，AI 一改就把用户手改冲掉。这里用锚点 patch 从根上避免。

### 决策 2：锚点 patch 局部回写（不做全量 HTML→MD 反序列化）

**两条路对比**：

| 方案 | 机制 | 问题 |
|---|---|---|
| 全量反序列化（预览壳现状） | 编辑后把整个 DOM 重新解析回 Markdown | 粗糙有损：self-intro 只回 name/role/edu/contact 丢了 gender/location/phone/email/links；依赖主题 class 名（`.org`/`.entry-title .role`），换主题就脆；一处对不上整份 MD 结构可能错乱 |
| **锚点 patch（采用）** | 装配时给每个可编辑原子打 `data-md` 锚点（标记对应 Markdown 的行号/片段 id）；编辑后只回写被改原子对应的片段，其余 MD 不动 | 局部替换、不动大结构 → 鲁棒；没改的字段不会丢；与主题解耦 |

**锚点注入点**：主题的 `render_header / render_entry / render_bullet / render_summary / render_stack` 都是纯函数返回 HTML 字符串，装配时（`assemble_html`）按解析顺序给每个原子带上行号锚点。例如：

```
MD:  - 主导推荐系统重构，DAU 提升 30%
装配: <li class="bullet" data-md-line="14">主导推荐系统重构…</li>
编辑: 用户把「30%」改成「45%」
回写: 只把 MD 第 14 行替换为新文本，其余行原样
```

**回写端点**：新增 `POST /resume/{id}/patch-draft`，接收「锚点 → 新文本」的 patch 列表，后端定位 checkpointer 当前草稿 MD 的对应行做替换，返回新版 MD（供前端刷新预览）。

**边界**：结构性改动（增删整段经历、调模块顺序）超出「改文字」范围，由 AI 对话承担——用户描述诉求，AI 改写 MD。手改只覆盖「文本内容替换」这一层，保底简单可靠。

### 决策 3：编辑回流的时机与不变量

**时机**：不做「编辑即同步」（频繁请求、checkpointer 写放大），改为**提交前 flush**：

- 用户发 AI 消息前 / 点定稿前 / 点导出 PDF 前，前端先把左侧当前编辑的 patch flush 到后端，更新 checkpointer 当前草稿。
- AI 改写永远基于 flush 后的最新 MD。

**不变量（贯穿整个交互）**：**iframe（预览壳）被新 MD 覆盖前，必须先 flush 当前编辑**。任何会触发 `srcdoc` 更新的路径（AI 改写返回、定稿、切版本）前，都要先 flush，否则用户未提交的编辑会被冲掉。代码里以一个 `flushEdits()` 前置调用守住。

### 决策 4：对话式保留 interrupt 范式，AI 回复结构化

**不升级成 ReAct**：精修子图仍是 `refine_setup → refine(interrupt) → finalize` 的 interrupt 多态（同构 mock-interview）。每条用户消息 = 一次 feedback，`Command(resume={action, feedback})` 唤醒。复用 checkpointer 跨轮记忆，后端内核零改动。

**AI 回复结构化**：现状 `refine_resume` 只产出新 Markdown。升级为产出「自然语言说明 + 改写后简历」两段，用轻量分隔符约定：

```
<<<REPLY>>>我把第二段经历的量化数据补上了，并前置了 AI 落地经验，你看左侧是否 OK。<<<RESUME>>>{新简历 Markdown 全文}
```

- 选分隔符而非 JSON：流式输出时 JSON 不完整无法解析，分隔符可边收边切，简单稳定。
- LLM 失控漏分隔符的降级：若 content 里没有 `<<<RESUME>>>`，把全部 content 当 reply，简历沿用上一版（不改写），并提示用户。

### 决策 5：流式三层——思考 / 回复 / 简历，各走各的呈现

接 reasoning stream 后，一次交互产生三层内容，对应三个来源、三种呈现：

| 层 | 来源（SSE） | 呈现 |
|---|---|---|
| 🧠 思考 | `reasoning` 事件（glm-4.5 `reasoning_content`） | 灰色斜体、可折叠、打字机逐字 |
| 💬 回复 | `token` 事件中 `<<<REPLY>>>` 段 | 正常气泡、打字机逐字（对话体感） |
| 📄 简历 | `token` 事件中 `<<<RESUME>>>` 段 | **不打字机**，完成后左侧整体刷新 |

**简历不打字机**沿用 add-reasoning-display 决策 5（用户反馈「简历逐字打字机没意义」）。后端按分隔符把 content 流切成 reply 段（边收边转发打字机）与 resume 段（攒着，完成时一次性随 `done` 下发完整新 MD，前端 assemble 刷新左侧）。

### 决策 6：思考过程不持久化历史，精修每轮实时生成

**不复用生成阶段的 reasoning 原文**：生成阶段的 reasoning 是 SSE 流过即焚，未落库；且全量 reasoning 可能数千字，塞进精修 prompt 既贵又稀释重点。

**改为实时**：精修每轮改写接 reasoning stream，用户每提一条反馈都能看到「AI 这次是怎么想的」。思考是针对本次修改的，比历史思考更相关。

**上次结果照常作上下文**：生成阶段的「简历 MD + 评估报告」本就持久化在 resume 表（`resume_id` 可查），精修 setup 时读出来作上下文——这部分不丢，只是「思考」从历史复用变成实时生成。**不动数据库，无迁移。**

### 决策 7：PDF 服务端渲染（Playwright），基于最新 MD 重新装配

**取代浏览器打印**：现状 `ResumePreview.printFrame()` 调 `frame.contentWindow.print()`，本质是浏览器打印对话框。改为服务端用 Playwright 起 Chromium 渲染 HTML → PDF，接口返回 `application/pdf`，浏览器直接下载。

**渲染源 = 最新 MD 重新装配**（非 iframe 即时 DOM）：导出时先 flush 手动编辑 → 以最新 MD 调 `assemble_html` + `wrap_preview` 重新装配 → Playwright 渲染该完整页。理由：守住「Markdown 单一真相源」，PDF 与预览同源、可复现；不把 iframe 里可能不一致的 DOM 当源。

**精确页数顺带兑现**：`resume_exporter.estimate_pages` 早有注释「精确页数/末页填充率需浏览器渲染，待 Playwright」——本决策一鱼两吃，导出与精确排版度量共用同一渲染路径。

**PDF 文件名**：沿用预览壳 `candidate()` 逻辑——「姓名-岗位」（从 self-intro 的 name + role 推导），与现有「PDF 默认文件名 SHALL 为姓名-岗位形式」一致。

### 决策 8：精修流式端点直接 orchestrate（实施时调整）

**原计划（决策 4）**：精修对话式保留 interrupt 范式，流式用 `graph.astream` + `writer` custom event 推 reasoning。

**实施时发现**：「astream × interrupt 子图 × Command resume × writer custom event」四者叠加在项目里**无先例**（生成阶段是主图 astream、无 interrupt）——node 内的 reasoning token 可能被 interrupt 暂停截断或 custom event 丢失，行为不可预期，需 spike 验证且风险高。

**调整**：refine 子图保留 interrupt + checkpointer 作**会话态存储**（`get_state` 读 / `update_state` 写草稿、评估、轮次、画像快照），但**流式路径在端点直接 orchestrate**——端点调 `refine_resume_reasoning_stream` 消费 reasoning stream、攒 content、`split_reply_resume` 切分、`evaluate_resume` 评估、`update_state` 写回，全程不 invoke/astream graph。Tasks 2 的 `patch-draft` 端点已用 `update_state` 不 invoke graph，先例成立、用法已验证。

**代价与权衡**：偏离了「interrupt 驱动流转」的纯粹范式（同步 `/refine` 仍走 interrupt，作降级通道），但会话态仍在 checkpointer（跨请求保持、抗重启），功能与记忆不丢；换来零风险的流式实现。面试讲点：**不为了范式一致而引入无先例的高风险组合**——范式服从工程现实，是成熟的取舍。

**对 reply 打字机的简化**：决策 5 原设 reply 打字机。实施时为避开「流式分隔符跨 chunk 切分」的复杂性与易错性，改为 reasoning 实时打字机（最有价值的思考过程实时出）+ content 攒齐后一次性切分（reply 一次性下发、resume 随 done 一次性）。reply 仅 1-3 句，一次性出体验可接受，换来切分逻辑的稳定与可单测。

### 决策 9：Windows + Playwright 的事件循环深坑（实施时踩中）

**现象**：服务端 PDF 渲染在 uvicorn 下抛 `NotImplementedError`（`asyncio._make_subprocess_transport`）。后端日志 `Using selector: SelectSelector`。

**根因链**：uvicorn 在 Windows 用 **SelectorEventLoop**（不支持 `create_subprocess_exec`），且**全局 asyncio policy 也是 Selector**。Playwright 启动 chromium 用子进程 → 失败。`asyncio.to_thread` 把 `sync_playwright` 放线程池**也没用**——sync_playwright 在线程内 `new_event_loop()` 读的是**全局 policy**，仍是 Selector。

**解法**（`resume_pdf.render_html_to_pdf`）：
1. 用 `sync_playwright`（同步 API，非 async）
2. 端点 `asyncio.to_thread` 放线程池（不阻塞 uvicorn loop）
3. render 内 `asyncio.set_event_loop_policy(WindowsProactorEventLoopPolicy)` 临时切 Proactor，`finally` 恢复原 policy；`sys.platform=='win32'` 守卫（Linux/mac 无此问题）

**验证坑**：`asyncio.run`（默认 Proactor）测不出——必须手动 `set_event_loop_policy(WindowsSelectorEventLoopPolicy)` 模拟 uvicorn 才能复现/验证修复。

**面试讲点**：跨平台 asyncio 子进程限制；不盲信「线程池隔离」——要懂 sync_playwright 内部仍读全局 policy；临时切 policy + 恢复的最小副作用解法。详见 memory `windows-playwright-pdf-policy`。

---

## 架构

```
┌──────────────────── 前端：ResumeRefine.vue（左右分栏工作台）────────────────────┐
│                                                                                │
│  ┌──────────── 左侧：简历工作区 ───────────┐   ┌──────── 右侧：AI 对话 ────────┐ │
│  │ ResumePreview (iframe, preview_shell)   │   │ 🤖 开场白：操作指引           │ │
│  │   预览态: 渲染 html                      │   │   · 直接点简历文字手动改      │ │
│  │   编辑态: contenteditable（原子带锚点）  │   │   · 或在这对话让我改          │ │
│  │                                          │   │ ─────────────────────        │ │
│  │  编辑 → 采集 patch（锚点→新文本）        │   │ 👤 把教育前置 + 第二段补量化 │ │
│  │     └─ postMessage 回传父页面           │   │ ─────────────────────        │ │
│  │                                          │   │ 🤖 🧠[思考] 灰斜体·可折叠    │ │
│  │  提交前/覆盖前: flushEdits() 不变量      │   │    💬 已前置，补了 DAU+30%…  │ │
│  │     └─ POST /patch-draft                │   │    📄 [简历已更新 v3] ◄ 刷新 │ │
│  │                                          │   │ ─────────────────────        │ │
│  │  AI 改写回 → assemble 刷新 srcdoc        │   │ [输入框]              [发送] │ │
│  │  [📄 导出 PDF] [✅ 满意定稿]             │   │                              │ │
│  └──────────────────────────────────────────┘   └──────────────────────────────┘ │
└─────────────────────────────────────┬──────────────────────────────────────────┘
                                      │ SSE: stage / reasoning / token / done / error
                                      ▼
┌──────────────────── 后端 ────────────────────┐
│  POST /resume/{id}/refine-stream  (新增, SSE 流式) │
│    refine_resume_reasoning_stream (openai client, glm-4.5)           │
│      reasoning → SSE reasoning                                      │
│      content: <<<REPLY>>>... 打字机 / <<<RESUME>>>... done 一次性    │
│    复用 refine 子图 interrupt + checkpointer                         │
│                                                                      │
│  POST /resume/{id}/patch-draft    (新增, 手动编辑局部回写)           │
│    锚点 patch → 替换 checkpointer 当前草稿 MD 对应行                 │
│                                                                      │
│  GET  /resume/{id}/pdf            (改造, 服务端渲染)                 │
│    flush → 最新 MD → assemble_html+wrap_preview → Playwright → PDF   │
│                                                                      │
│  assemble_html + render_*         加 data-md 锚点                    │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 与既有变更的关系

- **依赖 add-reasoning-display**：复用其 `stream_chat_with_reasoning` 公共层（openai client 直调 glm-4.5 读 `reasoning_content`）。该变更的 design 决策 4 只列了 generate / parse / match 接 reasoning，**未含 refine**——refine 的 reasoning 接入（含 reply/resume 分隔的特殊性）由本变更承接。
- **承接 add-streaming-pipeline 的 refine 流式**：该变更 tasks 中标注未完成的 refine 流式部分并入本变更一起做，spec 层面本变更新增 refine 专属 Requirement，不重复立项。
- **不动 mock-interview**：复用其长程会话范式（interrupt + checkpointer + Command resume），不改它。

---

## 风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| 锚点 patch 覆盖不全 | 某些可编辑原子没打锚点，手改回写时丢失 | 覆盖全部 render_* 产出的可编辑原子；patch 端点对「未命中锚点」告警；e2e 验证每种原子编辑后回写正确 |
| 结构性手改（增删经历）锚点无法表达 | 用户想加一段经历，patch 模型表达不了 | 手改只承诺「文本替换」；结构性改动引导用户走对话（AI 改写），开场白明示边界 |
| 精修 LLM 漏分隔符 | reply/resume 切不开 | 降级：无 `<<<RESUME>>>` 时 content 全当 reply，简历沿用上一版并提示；prompt 强约束 + 重试 |
| 服务端 PDF 依赖 Chromium 二进制 | 体积（~150MB）、部署、Windows 安装 | 用 Playwright 预编译 Chromium（非编译，通常顺利）；导出失败降级回浏览器打印并提示 |
| iframe srcdoc 重载丢编辑 | 用户未 flush 的编辑被新 MD 冲掉 | flushEdits() 不变量：所有覆盖路径前置 flush；代码 review 守住 |
| strong + reasoning 双段慢 | 精修每轮耗时长 | 流式保活防超时 + reasoning 让等待有内容 + 可折叠（同 add-reasoning-display 决策 7） |

---

## 面试讲解要点

1. **单一真相源 + 锚点局部回写**：所见即所得编辑与 AI 改写结合时的双源真相坑，用「Markdown 唯一真相 + HTML 派生 + 锚点 patch」从根上化解——体现架构思维，不是堆功能。
2. **复用长程会话范式**：精修对话式不重造轮子，复用 mock-interview 的 interrupt + checkpointer，加一个节点改交互外壳——状态机解耦的优势。
3. **reasoning 透明化延伸**：从生成阶段延伸到精修，且「思考/回复/简历」三层按内容性质分呈现粒度（简历不打字机）——产品 + 工程的双重判断。
4. **服务端端到端导出**：Playwright 渲染 PDF，既解决「浏览器打印不是导出」，又兑现早先埋下的精确页数伏笔——前后呼应、技术深度。
5. **不持久化历史思考的取舍**：明知「复用上次思考」是直觉需求，但权衡成本（DB 迁移）与效果（实时思考更相关）后选实时——能讲清为什么不这么做。
