<template>
  <el-config-provider :locale="zhCn">
    <router-view />
  </el-config-provider>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { ElConfigProvider } from 'element-plus';
import zhCn from 'element-plus/dist/locale/zh-cn.mjs';
import { useUserStore } from '@/stores/user';

// 初始化用户状态
const userStore = useUserStore();

onMounted(() => {
  userStore.initUserState();
});
</script>

<style lang="scss">
@import '@/styles/global.scss';
</style>
