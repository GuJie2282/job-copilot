# Design: 应用外壳与「我的画像」查看页

## Context

当前前端是「几个能跑的页面」，缺少把它们组织起来的应用外壳：

- 只有 [Home.vue](../../../web/src/views/Home.vue) 内嵌了一段 topbar（复制粘贴进去的）；[ResumeParser.vue](../../../web/src/views/ResumeParser.vue) 与 [JdMatcher.vue](../../../web/src/views/JdMatcher.vue) 只有 `page-head`，没有任何导航/退出/返回，进入即孤岛。
- 画像只在简历解析成功那一刻由 `ProfileDisplay` 显示，刷新或离开就消失——尽管后端 [getProfile](../../../web/src/api/resume.ts) / `exportProfile` 早已齐全，画像也已持久化。
- 首页是单列 4 个入口按钮，无任何用户真实数据回流。
- [UploadGuide.vue](../../../web/src/components/UploadGuide.vue) 占地大，且其「查看示例简历」按钮 emit 的 `viewSample` 从未被 [InputSelector.vue](../../../web/src/components/InputSelector.vue) 监听（死按钮）。

约束（来自 CLAUDE.md）：负责人技术背景弱，代码要中文注释、循序渐进；**简单优先**，不过度抽象、不提前优化；这是面试作品集，技术选型要能讲出道理。设计系统已在上一轮统一（token / 宋体大标题 / 墨蓝 + 琥珀，Element Plus 已通过 CSS 变量桥接）。

## Goals / Non-Goals

**Goals:**
- 一条全局顶栏贯穿所有内容页（导航 + 位置感 + 退出），Login/Register 保持沉浸式。
- 画像成为一等公民：有独立 URL `/profile`，可随时查看与编辑。
- 首页用**真实数据**（画像摘要 + 最近匹配）撑起质感，新用户有空状态引导。
- 清掉 UploadGuide（连死按钮一起）。

**Non-Goals:**
- 不做浏览器式「← 返回」按钮（顶栏导航 + logo 回首页已覆盖）。
- 不做左侧栏布局（功能尚未多到需要；移动端复杂度不划算）。
- 不实现简历优化 / 模拟面试（保持灰显）。
- 不改后端、不新增后端接口。
- 不做画像/匹配的跨页缓存（MVP 可接受重复请求）。

## Decisions

### 1. 顶栏在 App.vue 按 `route.meta.chrome` 渲染（而非每页粘贴 / 嵌套路由）
- **选**：给需要顶栏的路由加 `meta: { chrome: true }`，[App.vue](../../../web/src/App.vue) 里 `v-if` 渲染 `AppTopBar`，下方放 `<router-view />`。
- **备选 a**：每个页面各自 import 顶栏——这正是现状痛点（Home 那段是抄的），重复且易漏。
- **备选 b**：Vue Router 嵌套 `children` + layout 组件——更「正统」，但要重构整张路由表，复杂度高，违背简单优先。
- **理由**：meta + App.vue 一处控制、改动最小、DRY。默认不渲染（只有标 `chrome:true` 的才渲染），Login/Register 天然不带顶栏。

### 2. 顶栏导航项 = 首页 / 我的画像 / 匹配，用 `router-link` + active class 高亮
- 三项分别对应 `/`、`/profile`、`/jd-matcher`，用 `router-link` 的 `active-class` 自动高亮当前页。
- 退出登录复用 Home 现有 `ElMessageBox.confirm` 流程，整体迁入 `AppTopBar`；Home 内不再单独放退出逻辑。

### 3. 我的画像页复用现有组件，不新写展示/编辑逻辑
- `/profile` 调 [getProfile](../../../web/src/api/resume.ts) 取数 → 用 `ProfileDisplay` 展示 → 监听其 `edit` 切到 `ProfileEditor` → 监听 `save` 调 `updateProfile`。
- **理由**：`ProfileDisplay` / `ProfileEditor` 已完整，复用 = 零新展示逻辑、最低风险。props 对齐（`profile` + `confidence`），实现时若字段不符，在 `Profile.vue` 侧适配，尽量不动组件本身。

### 4. 首页看板取数：getProfile + matchHistory，画像摘要只显真实计数
- 画像摘要卡直接读 profile 字段计数（经历条数 = `companies.length`、技能项数 = 技能数组合计）。**不显示完成度百分比**（用户拍板：算分容易做虚，诚实计数更有信息量）。
- 最近匹配卡复用 JdMatcher 的 matchHistory；实现第一步确认其返回结构——若不利于首页摘要展示，降级为「前往查看全部匹配」入口（不阻塞）。

### 5. 空状态优先：空 = 引导，错 = 提示
- 首页无画像 → 大 CTA「开始建立画像 →」跳 `/resume-parser`。
- `/profile` 无画像 → 引导跳 `/resume-parser`。
- 请求失败 → 错误提示 + 重试（不阻断页面其余部分）。
- 语义分清楚：**建立画像**（ResumeParser，输入）vs **我的画像**（`/profile`，查看/编辑）。

### 6. 删 UploadGuide
- 从 [InputSelector.vue](../../../web/src/components/InputSelector.vue) 移除 `<UploadGuide>` 引用 + 删除 `UploadGuide.vue` 文件。
- 格式限制信息已在 [FileUpload.vue](../../../web/src/components/FileUpload.vue) 上传区写明（支持 PDF/Word、最大 10MB）；不支持的格式等真出错时由 `ErrorHandler` 提示——「失败即指引」，比前置堆说明更克制。

### 7. 视觉沿用现有设计系统，零新风格
- `AppTopBar` = Home 现有 topbar 提炼为独立组件（logo「求」方块 + 导航 + 头像 dropdown）。
- 看板卡片用现有细边框 + `.card` 风格；标题继承全局宋体。不引入新色、不加 emoji、不加渐变。

## Risks / Trade-offs

- **[App.vue 全局渲染顶栏，怕 Login/Register 误显示]** → 用 `meta.chrome` 显式开关，且默认不渲染（只有标 true 才渲染）。验收时逐一确认 5 个路由。
- **[Home 与 /profile 都调 getProfile，重复请求]** → MVP 可接受（低频页面进入）。后续可上 `userStore` 缓存，非本次目标。
- **[matchHistory 返回结构未确认]** → 实现第一步核对；不兼容则最近匹配卡降级为入口链接，不阻塞主流程。
- **[ProfileDisplay/Editor 原耦合 ResumeParser 的 parseResult 结构]** → 复用时 props 对齐验证；必要时在 `Profile.vue` 适配而非改组件，避免回归 ResumeParser。
- **[删 UploadGuide 后用户不知格式限制]** → 上传区已含摘要 + 失败时 ErrorHandler 提示，可接受。

## Migration Plan

纯前端，无数据迁移。建议提交顺序（每步可独立验证）：

1. `AppTopBar.vue` + `App.vue`（meta.chrome 渲染）+ `router/index.ts`（各路由加 meta）→ 顶栏立即可见，导航可用。
2. `Profile.vue` + `/profile` 路由 → 画像可独立查看/编辑。
3. `Home.vue` 看板重写 → 首页有真实数据与空状态。
4. 删 `UploadGuide`（InputSelector 移除引用 + 删文件）。

回滚：每步独立 commit，`git revert` 单个 commit 即可，无副作用。

## Open Questions

- `matchHistory` 的确切返回结构（实现第 3 步前核对）。
- `ProfileDisplay` / `ProfileEditor` 在 `/profile` 复用时的 action（edit/save）对接是否需要微调——实现时验证。
