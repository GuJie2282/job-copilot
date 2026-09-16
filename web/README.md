# 求职 Copilot Web

基于 Vue 3 + TypeScript + Element Plus 的求职 Copilot 前端项目。

## 技术栈

- **Vue 3** - 渐进式 JavaScript 框架
- **TypeScript** - JavaScript 的超集，提供静态类型检查
- **Vite** - 下一代前端构建工具
- **Element Plus** - Vue 3 UI 组件库
- **Pinia** - Vue 3 官方推荐的状态管理库
- **Vue Router** - Vue 3 官方路由
- **Axios** - HTTP 客户端
- **SCSS** - CSS 预处理器

## 项目结构

```
web/
├── src/
│   ├── api/           # API 接口
│   ├── assets/        # 静态资源
│   ├── components/    # 公共组件
│   ├── router/        # 路由配置
│   ├── stores/        # Pinia 状态管理
│   ├── styles/        # 全局样式
│   ├── types/         # TypeScript 类型定义
│   ├── views/         # 页面组件
│   ├── App.vue        # 根组件
│   └── main.ts        # 入口文件
├── index.html         # HTML 模板
├── vite.config.ts     # Vite 配置
├── tsconfig.json      # TypeScript 配置
└── package.json       # 项目依赖

## 开发指南

### 安装依赖

```bash
cd web
npm install
```

### 启动开发服务器

```bash
npm run dev
```

开发服务器将在 http://localhost:3000 启动。

### 构建生产版本

```bash
npm run build
```

### 预览生产构建

```bash
npm run preview
```

## 功能特性

- ✅ 用户登录/注册 + 验证码 + JWT 身份验证
- ✅ 简历解析 / 画像编辑（上传 PDF·Word 或粘贴文本）
- ✅ JD 匹配（匹配度 + 维度打分 + 差距清单，SSE 流式增量渲染）
- ✅ 简历优化 / 精修工作台 / 历史版本 / 多主题 PDF 导出
- ✅ 模拟面试（配置 → 面试间 → 复盘报告；文字与语音作答）
- ✅ 面经库（个人沉淀 + 公司真题，语义检索）
- ✅ 响应式设计（桌面 / 移动端）· TypeScript 严格模式 · 路由守卫 · API 错误处理

## 目录结构

```
web/
├── src/
│   ├── views/          # 页面：登录/注册/首页/画像/JD匹配/简历×4/面试×4/面经库
│   ├── components/     # 公共组件
│   ├── api/            # 接口层（axios 封装，含 SSE 流式请求）
│   ├── stores/         # Pinia 状态
│   ├── router/         # 路由 + 守卫
│   ├── styles/         # 全局样式 / 设计 token
│   └── types/          # TypeScript 类型
└── tests/e2e/          # Playwright 端到端测试
```

> 前端依赖后端：请先在 `../backend` 启动 8001 端口的服务，否则页面接口全部报错。

## 设计规范

### 色彩系统

- **主色调**: `#2563eb` - 专业可信赖的蓝色
- **辅助色**: `#f59e0b` - 温暖鼓励的橙色
- **成功色**: `#10b981`
- **警告色**: `#f59e0b`
- **错误色**: `#ef4444`

### 组件规范

- **卡片圆角**: 8px
- **按钮圆角**: 8px
- **阴影**: `0 1px 3px rgba(0,0,0,0.1)`
- **主按钮**: 使用主色背景
- **次要按钮**: 描边样式

## 环境变量

| 文件 | 变量 | 值 | 说明 |
|---|---|---|---|
| `.env.development` | `VITE_API_BASE_URL` | `/api` | 普通 JSON 请求走 vite dev proxy → `localhost:8001` |
| `.env.development` | `VITE_STREAM_BASE_URL` | `http://localhost:8001/api` | SSE 流式请求直连后端（vite proxy 不转发 `text/event-stream`） |
| `.env.production` | `VITE_API_BASE_URL` | `https://api.jobcopilot.com/api` | **占位值，项目尚未部署**，上线时需改成真实域名 |

> 为什么流式请求要绕开 proxy：vite dev proxy 会把 `text/event-stream` 缓冲住（实测 150s 透传 0 字节、连接挂起），所以 SSE 端点直连后端，其余请求仍走 proxy。
>
> 内网穿透（cpolar 等）联调时会用 `--mode cpolar` 启动，配置见 `.env.cpolar`（含个人隧道地址，未纳入版本管理）。

## 浏览器支持

- Chrome >= 87
- Firefox >= 78
- Safari >= 14
- Edge >= 88

## License

MIT
