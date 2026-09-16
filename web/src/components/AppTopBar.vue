<template>
  <!-- 全局顶栏：所有「内容页」共用（登录/注册页不渲染，见 App.vue 的 meta.chrome 判断） -->
  <header class="topbar">
    <div class="topbar-inner">
      <!-- 左：logo，点击回首页 -->
      <!-- 返回上一页（非首页显示；无浏览历史则回首页兜底） -->
      <button v-if="!isHome" class="back-btn" type="button" @click="goBack" aria-label="返回上一页">
        <span class="back-arrow">←</span><span class="back-text">返回</span>
      </button>
      <router-link to="/" class="logo">
        <span class="logo-mark">求</span>
        <span class="logo-name">求职 Copilot</span>
      </router-link>

      <!-- 主导航：用 router-link 的 exact-active-class 在「精确处于该路由」时高亮 -->
      <nav class="nav">
        <router-link to="/" class="nav-item" exact-active-class="is-active">首页</router-link>
        <router-link to="/profile" class="nav-item" exact-active-class="is-active">我的画像</router-link>
        <router-link to="/jd-matcher" class="nav-item" exact-active-class="is-active">JD匹配</router-link>
        <router-link to="/resume-optimizer" class="nav-item" exact-active-class="is-active">简历优化</router-link>
        <router-link to="/interview/setup" class="nav-item" active-class="is-active">模拟面试</router-link>
        <router-link to="/interview/library" class="nav-item" active-class="is-active">面经库</router-link>
      </nav>

      <!-- 右：用户菜单（头像下拉 → 我的画像 / 退出登录） -->
      <el-dropdown @command="onCommand">
        <span class="user">
          <el-avatar :size="32" class="avatar">{{ userStore.userName.charAt(0) }}</el-avatar>
          <span class="user-name">{{ userStore.userName }}</span>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="profile">我的画像</el-dropdown-item>
            <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>

<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'
import { computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

// 当前是否首页（首页是根，不显示返回按钮）
const isHome = computed(() => route.path === '/')

/** 返回上一页；无浏览历史则回首页兜底 */
function goBack(): void {
  if (window.history.length > 1) {
    router.back()
  } else {
    router.push('/')
  }
}

/** 用户菜单命令分发 */
async function onCommand(command: string): Promise<void> {
  if (command === 'profile') {
    router.push('/profile')
    return
  }
  if (command === 'logout') {
    await handleLogout()
  }
}

/** 退出登录：确认 → 清状态 → 回登录页（逻辑从 Home.vue 迁移至此，全局复用） */
async function handleLogout(): Promise<void> {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await userStore.logout()
    ElMessage.success('已退出登录')
    router.push('/login')
  } catch (error) {
    // 用户点「取消」会 reject 'cancel'，属正常流程，忽略
    if (error !== 'cancel') {
      console.error('退出登录失败:', error)
    }
  }
}
</script>

<style scoped lang="scss">
.topbar {
  background: $bg-white;
  border-bottom: 1px solid $border-color;
  position: sticky;
  top: 0;
  z-index: $z-sticky;
}

.topbar-inner {
  max-width: $container-xl;
  margin: 0 auto;
  padding: 0 $spacing-xl;
  height: 64px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: $spacing-xl;
}

/* 返回按钮（非首页显示） */
.back-btn {
  display: inline-flex;
  align-items: center;
  gap: $spacing-xs;
  background: none;
  border: 1px solid $border-color;
  border-radius: $radius-md;
  padding: $spacing-xs $spacing-sm;
  color: $text-secondary;
  font-size: $font-size-sm;
  cursor: pointer;
  transition: all $transition-base ease;

  &:hover {
    border-color: $primary-color;
    color: $primary-color;
  }

  .back-arrow {
    font-size: $font-size-base;
    line-height: 1;
  }
}

/* logo */
.logo {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  text-decoration: none;
}

.logo-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: 1.5px solid $accent-color;
  color: $accent-color;
  font-family: $font-heading;
  font-size: $font-size-lg;
  font-weight: $font-weight-bold;
  border-radius: $radius-md;
}

.logo-name {
  font-family: $font-heading;
  font-size: $font-size-lg;
  font-weight: $font-weight-semibold;
  color: $ink;
}

/* 主导航：推到右侧，紧邻用户菜单 */
.nav {
  display: flex;
  align-items: center;
  gap: $spacing-lg;
  margin-left: auto;
}

.nav-item {
  font-size: $font-size-sm;
  color: $text-secondary;
  text-decoration: none;
  padding: $spacing-xs 0;
  border-bottom: 2px solid transparent;
  transition: color $transition-base ease;
  /* 不许被压缩：flex 默认会挤窄导航项，中文被压到只剩一两个字宽就会竖排成
     「我/的/画/像」，比整体换行难看得多。宁可换行/溢出，也不要单字竖排。 */
  flex-shrink: 0;
  white-space: nowrap;

  &:hover {
    color: $ink;
  }

  /* 当前页高亮：底部琥珀细线 + 加粗墨蓝 */
  &.is-active {
    color: $ink;
    font-weight: $font-weight-semibold;
    border-bottom-color: $accent-color;
  }
}

/* 用户菜单 */
.user {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  cursor: pointer;
  padding: $spacing-xs $spacing-sm;
  border-radius: $radius-md;
  transition: background $transition-base ease;
  outline: none;

  &:hover {
    background: $bg-gray;
  }
}

.avatar {
  background: $primary-color;
  color: #fff;
  font-weight: $font-weight-semibold;
}

.user-name {
  font-size: $font-size-sm;
  color: $text-primary;
}

@media (max-width: $container-md) {
  .topbar-inner {
    padding: 0 $spacing-lg;
    gap: $spacing-md;
  }

  /* 窄屏隐藏用户名，只留头像，给导航腾位 */
  .user-name {
    display: none;
  }

  .nav {
    gap: $spacing-md;
  }
}

/* 手机宽度：导航已到 6 项，一行放不下了，改成两行——上行 logo/头像，下行整条导航。
   不这么做的话导航会被挤出顶栏（实测临界点约 470px）。
   与上面「窄屏收起用户名」是同一套思路：空间不够时先收文字、再换行，别硬挤。 */
@media (max-width: $container-sm) {
  .topbar-inner {
    height: auto;
    min-height: 64px;
    flex-wrap: wrap;
    padding: $spacing-sm $spacing-lg;
  }

  .logo-name {
    display: none;
  }

  /* 导航整行铺开、居中，换行时不跟 logo 抢位置 */
  .nav {
    order: 3;
    width: 100%;
    margin-left: 0;
    justify-content: center;
    flex-wrap: wrap;
    row-gap: $spacing-xs;
  }
}
</style>
