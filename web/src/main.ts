/**
 * 应用入口文件
 */
import { createApp } from 'vue';
import { createPinia } from 'pinia';
import ElementPlus from 'element-plus';
import * as ElementPlusIconsVue from '@element-plus/icons-vue';
import 'element-plus/dist/index.css';
// 标题字体：思源宋体（自托管，随站点打包，国内 100% 可达）
// 只引入「简中子集 + 标题字重 600/700」，避免把拉丁/西里尔全字重打进包
import '@fontsource/noto-serif-sc/chinese-simplified-600.css';
import '@fontsource/noto-serif-sc/chinese-simplified-700.css';
import App from './App.vue';
import router from './router';

const app = createApp(App);

// 创建 Pinia 状态管理
const pinia = createPinia();
app.use(pinia);

// 使用路由
app.use(router);

// 使用 Element Plus
app.use(ElementPlus);

// 注册所有图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component);
}

// 挂载应用
app.mount('#app');
