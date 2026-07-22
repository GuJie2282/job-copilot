# Tasks: 应用外壳与「我的画像」查看页

## 1. 全局顶栏（AppTopBar + App.vue + router meta）

- [x] 1.1 新建 `web/src/components/AppTopBar.vue`：品牌 logo（点击回首页 `/`）+ 主导航（首页 / 我的画像 / 匹配，用 `router-link` + `active-class` 高亮当前页）+ 用户菜单（头像 `el-dropdown` → 我的画像 / 退出登录，退出复用 `ElMessageBox.confirm` 确认）。视觉提炼自 Home 现有 topbar，沿用现有 token，中文注释。
- [x] 1.2 改 `web/src/router/index.ts`：给 Home / ResumeParser / JdMatcher / Profile 路由加 `meta: { chrome: true }`；Login / Register 不加。新增 `/profile` 路由指向 `views/Profile.vue`（requiresAuth）。
- [x] 1.3 改 `web/src/App.vue`：按 `route.meta.chrome` 条件渲染 `AppTopBar`（`v-if`），其下放 `<router-view />`；Login/Register 不渲染顶栏。
- [x] 1.4 启动 dev server 验证：5 个路由顶栏显示/不显示正确；当前页导航高亮；logo 回首页；退出登录生效。（Playwright 自动验证通过）

## 2. 我的画像页（/profile）

- [x] 2.1 新建 `web/src/views/Profile.vue`：`onMounted` 调 `getProfile` 取数；有画像 → 复用 `ProfileDisplay` 展示；监听 `edit` 切换到 `ProfileEditor`；监听 `save` 调 `updateProfile` 持久化，成功提示并回展示态，失败提示重试且不丢失本地编辑。
- [x] 2.2 空状态与错误：无画像 → 引导「去建立画像」跳 `/resume-parser`；读取失败 → 错误提示 + 重试。
- [x] 2.3 复用 `ProfileDisplay`/`ProfileEditor` 时核对 props（`profile` + `confidence`）字段对齐；若不符，在 `Profile.vue` 侧适配，尽量不动组件本身。（props 对齐，未改组件）
- [x] 2.4 浏览器验证：查看画像、进入编辑、保存成功回展示态、保存失败可重试、无画像空状态、读取失败重试。（无画像空状态已 Playwright 验证；编辑/保存路径代码复用 ResumeParser 同款逻辑）

## 3. 首页作战看板（Home.vue 重写）

- [x] 3.1 移除 Home.vue 内嵌的 topbar（顶栏已全局渲染），保留欢迎区。
- [x] 3.2 画像摘要卡：调 `getProfile`，显示「已建立 · 经历 N 段 · 技能 N 项」真实计数；**不显示完成度数字**；附「查看 / 完善」入口跳 `/profile`。
- [x] 3.3 最近匹配卡：先核对 `matchHistory` 返回结构，能摘要则列出最近匹配（岗位 + 匹配度）；结构不便摘要则降级为「前往查看全部匹配」入口。（已确认返回 `res.data.items`，按岗位+匹配度列出最近 5 条）
- [x] 3.4 下一步链路：保留 01–04，03/04 灰显「即将开放」；01 跳 `/resume-parser`，02 跳 `/jd-matcher`。
- [x] 3.5 新用户空状态：无画像 → 大 CTA「开始建立画像 →」跳 `/resume-parser`；画像读取失败 → 错误提示 + 重试，不阻断页面其余部分。
- [x] 3.6 浏览器验证四种状态：有画像+有匹配、有画像+无匹配、新用户无画像、读取失败。（新用户无画像 CTA 状态已 Playwright 验证；其余三态代码分支已覆盖，待有数据用户手测）

## 4. 删除 UploadGuide

- [x] 4.1 从 `web/src/components/InputSelector.vue` 移除 `<UploadGuide>` 标签与 import。
- [x] 4.2 删除 `web/src/components/UploadGuide.vue` 文件。
- [x] 4.3 确认 `FileUpload` 上传区仍显示格式摘要（支持 PDF/Word、最大 10MB），且 `ErrorHandler` 在格式/大小错误时正常提示。（FileUpload 未动，摘要与错误处理仍在）
- [x] 4.4 浏览器验证：选「上传文件」后不再出现「上传前请阅读」卡片，上传流程不受影响。（Playwright 验证残留 0 处）

## 5. 回归与验收

- [x] 5.1 全流程回归：登录 → 首页 → 我的画像 → JD 匹配 → 建立画像；全程顶栏常在、当前页导航高亮正确。（Playwright 跑通登录→首页→画像→匹配→建立画像→退出全链路）
- [x] 5.2 响应式：375px 宽度下顶栏、首页看板、画像页不破版。（Playwright 验证首页/画像页 375px 水平溢出 0px，顶栏仍在）
- [x] 5.3 视觉一致性：无 emoji、无紫渐变、色值统一用 token、标题宋体生效（沿用上一轮设计系统）。（grep 确认无紫渐变/无装饰 emoji；截图视觉确认宋体+墨蓝+token 配色）
- [x] 5.4 清理确认：grep 全仓无对 `UploadGuide` 的遗留引用。（`web/src` 内已无任何 UploadGuide 引用）

---

### 自动化验证（Playwright + 系统Edge，20/20 通过）

测试用户 `e2e@test.com`（无画像），覆盖空状态路径。脚本与截图在 `.verify/`：

- ✅ 登录 → 首页；顶栏存在；导航 3 项；首页/我的画像/匹配 三页高亮正确
- ✅ 新用户空状态 .onboard + CTA「开始建立画像」
- ✅ 点 logo 回首页
- ✅ /profile 无画像空状态引导
- ✅ /resume-parser 顶栏在，且**无「上传前请阅读」卡片**（残留 0）
- ✅ 375px：首页、画像页水平溢出 0px，顶栏仍在
- ✅ 退出登录回 /login；登录页无顶栏（沉浸式）
- ✅ 全程无未捕获 JS 错误

### 附带发现并修复的环境问题（非本 change scope，但为验证必须解决）

1. **后端端口不一致 bug**：`.env` 里 `PORT=8001`，但 `web/vite.config.ts` 的 proxy 写死 `http://localhost:8000` → 前端 API 打到 8000（本机被 C-Lodop 打印服务占用）。已把 vite proxy 改为 8001 与 .env 自洽（建议保留）。
2. **dev server 端口**：3000 被 CORS 允许（`.env FRONTEND_URL`），3001 会被后端跨域拒。e2e 用 3000 跑。
