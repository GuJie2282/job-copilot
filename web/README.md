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

- ✅ 用户登录/注册
- ✅ 验证码验证
- ✅ JWT 身份验证
- ✅ 响应式设计
- ✅ TypeScript 严格模式
- ✅ 路由守卫
- ✅ API 错误处理
- ✅ 现代化简约设计

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

### 开发环境 (.env.development)
```
VITE_API_BASE_URL=http://localhost:8000/api
```

### 生产环境 (.env.production)
```
VITE_API_BASE_URL=https://api.jobcopilot.com/api
```

## 浏览器支持

- Chrome >= 87
- Firefox >= 78
- Safari >= 14
- Edge >= 88

## License

MIT
