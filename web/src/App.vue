<template>
  <el-config-provider :locale="zhCn">
    <!-- 全局顶栏：仅当路由 meta.chrome 为 true 时渲染。
         内容页（首页/建立画像/JD匹配/我的画像）显示，登录/注册页保持沉浸式分屏不显示。 -->
    <AppTopBar v-if="route.meta['chrome']" />
    <router-view />
  </el-config-provider>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { ElConfigProvider } from 'element-plus';
import zhCn from 'element-plus/dist/locale/zh-cn.mjs';
import { useUserStore } from '@/stores/user';
import AppTopBar from '@/components/AppTopBar.vue';

// 初始化用户状态
const userStore = useUserStore();
const route = useRoute();

onMounted(() => {
  userStore.initUserState();
});
</script>

<style lang="scss">
@use '@/styles/global.scss';
</style>
