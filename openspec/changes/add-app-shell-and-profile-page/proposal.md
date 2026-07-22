# Proposal: 应用外壳与「我的画像」查看页

## Why

前端目前缺一个贯穿所有页面的「应用外壳」：只有首页有顶栏导航，建立画像页（ResumeParser）与 JD 匹配页（JdMatcher）只有页头、没有任何导航/退出/返回入口，进入后即成孤岛，只能靠浏览器后退；画像虽已持久化（后端 `getProfile` / `exportProfile` 接口齐全），却没有独立查看入口，只在解析成功那一刻可见，刷新或离开就消失；首页仅 4 个入口按钮、无任何用户真实数据回流，空且缺乏质感；此外「上传前请阅读」组件（UploadGuide）占用空间过大，且其「查看示例简历」按钮从未被监听（死按钮）。

这些症状同源于一个根因——缺少信息架构层面的外壳与导航。本次为前端补上这套外壳，让产品从「几个能跑的页面」变成「一个能导航、有位置感的产品」。这是 AI PM 视角（功能 → 体验 → 信息架构）的体现，也是面试主讲点。

## What Changes

- **新增全局顶栏组件 `AppTopBar`**：logo（点击回首页）+ 主导航（首页 / 我的画像 / 匹配，当前页高亮）+ 用户菜单（头像 dropdown → 我的画像 / 退出登录）。视觉提炼自 Home 现有 topbar，沿用现有 token。
- **路由按 `meta: { chrome: true }` 条件渲染顶栏**：Home / ResumeParser / JdMatcher / 新 Profile 页显示顶栏；Login / Register 保持沉浸式分屏，不显示。在 `App.vue` 统一渲染，避免各页重复粘贴顶栏。
- **新增「我的画像」页 `/profile`**：用 `getProfile` 取数，复用 ProfileDisplay 展示、ProfileEditor 编辑，空状态引导去建立画像。建立画像（ResumeParser，输入）与查看画像（/profile，查看/编辑）语义分离。
- **首页 Home 重构为「作战看板」**：画像摘要卡（已建立 · 经历 N 段 · 技能 N 项，不显示完成度数字）+ 最近匹配卡（复用 matchHistory）+ 下一步链路（01–04，03/04 灰显「即将开放」）。新用户空状态为大 CTA「开始建立画像 →」。
- **删除 `UploadGuide` 组件**并从 `InputSelector` 移除引用——关键格式说明已在 FileUpload 上传区体现（支持 PDF/Word、最大 10MB），格式不支持的细节等真出错时由 ErrorHandler 提示（失败即指引）。

视觉完全沿用上一轮建立的设计系统（token / 宋体大标题 / 墨蓝 + 琥珀），不引入新风格、不加 emoji、不加紫渐变。**不改后端、不新增后端接口。**

## Capabilities

### New Capabilities

- `app-shell`: 前端应用外壳——全局顶栏导航、按路由渲染页面外壳、首页作战看板（含画像摘要与最近匹配）、「我的画像」独立查看页，以及各内页具备导航与位置感。覆盖「页面之间如何连通、用户当前在哪儿、能去哪儿」的信息架构层。

### Modified Capabilities

本变更不修改任何已归档 spec 的需求。画像查看页消费的是 user-profile 已具备的「读取画像」数据能力（见 `add-resume-parsing-and-profile-creation` 的画像持久化 Requirement），不改变其数据语义，故不作为对 user-profile 的 spec 级修改。

## Impact

- **受影响代码（纯前端）**：
  - 新增：`web/src/components/AppTopBar.vue`、`web/src/views/Profile.vue`
  - 修改：`web/src/App.vue`（按 meta.chrome 渲染顶栏）、`web/src/router/index.ts`（新增 /profile 路由 + 各路由 chrome meta）、`web/src/views/Home.vue`（看板重写）、`web/src/components/InputSelector.vue`（移除 UploadGuide 引用）
  - 删除：`web/src/components/UploadGuide.vue`
- **数据依赖**：复用现有后端接口 `GET /resume/profile`（getProfile）与 JD 匹配历史读取；无新接口、无后端改动。
- **不影响**：后端、数据库、鉴权流程、简历解析与 JD 匹配的业务逻辑。
- **非目标**：不加浏览器式「← 返回」按钮（顶栏导航 + logo 回首页已覆盖返回需求）；不实现简历优化 / 模拟面试（保持灰显）。
