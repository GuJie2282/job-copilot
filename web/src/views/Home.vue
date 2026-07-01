<template>
  <div class="home-container">
    <el-container>
      <!-- 顶部导航 -->
      <el-header class="header">
        <div class="header-content">
          <div class="logo">
            <el-icon :size="32" color="#2563eb">
              <UserFilled />
            </el-icon>
            <span class="logo-text">求职 Copilot</span>
          </div>
          <div class="user-menu">
          <el-dropdown @command="handleLogout">
            <span class="user-name">
              <el-avatar :size="32" class="avatar">
                {{ userStore.userName.charAt(0) }}
              </el-avatar>
              <span>{{ userStore.userName }}</span>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          </div>
        </div>
      </el-header>

      <!-- 主要内容 -->
      <el-main class="main-content">
        <div class="welcome-section">
          <h1>欢迎回来，{{ userStore.userName }}！</h1>
          <p class="subtitle">你的求职教练已准备就绪</p>
        </div>

        <!-- 快捷入口卡片 -->
        <div class="quick-actions">
          <el-row :gutter="24">
            <el-col :xs="24" :sm="12" :md="8">
              <el-card class="action-card" shadow="hover">
                <div class="card-content">
                  <el-icon :size="48" color="#2563eb">
                    <Document />
                  </el-icon>
                  <h3>JD 匹配</h3>
                  <p>分析职位描述，了解匹配度</p>
                </div>
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="12" :md="8">
              <el-card class="action-card" shadow="hover">
                <div class="card-content">
                  <el-icon :size="48" color="#10b981">
                    <Edit />
                  </el-icon>
                  <h3>简历优化</h3>
                  <p>AI 智能优化，提升竞争力</p>
                </div>
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="12" :md="8">
              <el-card class="action-card" shadow="hover">
                <div class="card-content">
                  <el-icon :size="48" color="#f59e0b">
                    <ChatDotSquare />
                  </el-icon>
                  <h3>模拟面试</h3>
                  <p>真实场景练习，从容应对</p>
                </div>
              </el-card>
            </el-col>
          </el-row>
        </div>

        <!-- 求职进度看板 -->
        <el-card class="progress-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <h2>求职进度</h2>
            </div>
          </template>
          <el-row :gutter="24" class="progress-stats">
            <el-col :xs="12" :sm="6">
              <div class="stat-item">
                <div class="stat-value">0</div>
                <div class="stat-label">已投递</div>
              </div>
            </el-col>
            <el-col :xs="12" :sm="6">
              <div class="stat-item">
                <div class="stat-value">0</div>
                <div class="stat-label">面试中</div>
              </div>
            </el-col>
            <el-col :xs="12" :sm="6">
              <div class="stat-item">
                <div class="stat-value">0</div>
                <div class="stat-label">Offer</div>
              </div>
            </el-col>
            <el-col :xs="12" :sm="6">
              <div class="stat-item">
                <div class="stat-value">0%</div>
                <div class="stat-label">通过率</div>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-main>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { UserFilled, Document, Edit, ChatDotSquare } from '@element-plus/icons-vue';
import { useUserStore } from '@/stores/user';

// 路由
const router = useRouter();

// 状态管理
const userStore = useUserStore();

/**
 * 退出登录
 */
const handleLogout = async (): Promise<void> => {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    });

    await userStore.logout();
    ElMessage.success('已退出登录');
    router.push('/login');
  } catch (error) {
    // 用户取消操作
    if (error !== 'cancel') {
      console.error('退出登录失败:', error);
    }
  }
};
</script>

<style scoped lang="scss">
@import '@/styles/variables.scss';

.home-container {
  min-height: 100vh;
  background: $bg-light;
}

.header {
  background: $bg-white;
  box-shadow: $shadow-sm;
  padding: 0;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 100%;
  max-width: $container-xl;
  margin: 0 auto;
  padding: 0 $spacing-xl;
}

.logo {
  display: flex;
  align-items: center;
  gap: $spacing-sm;

  .logo-text {
    font-size: $font-size-xl;
    font-weight: $font-weight-bold;
    color: $primary-color;
  }
}

.user-menu {
  .user-name {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    cursor: pointer;
    padding: $spacing-sm;
    border-radius: $radius-md;
    transition: background $transition-base ease;

    &:hover {
      background: $bg-light;
    }
  }

  .avatar {
    background: $primary-color;
    color: $bg-white;
    font-weight: $font-weight-semibold;
  }
}

.main-content {
  max-width: $container-xl;
  margin: 0 auto;
  padding: $spacing-2xl $spacing-xl;
}

.welcome-section {
  text-align: center;
  margin-bottom: $spacing-2xl;

  h1 {
    font-size: $font-size-3xl;
    font-weight: $font-weight-bold;
    color: $text-primary;
    margin-bottom: $spacing-sm;
  }

  .subtitle {
    font-size: $font-size-lg;
    color: $text-secondary;
  }
}

.quick-actions {
  margin-bottom: $spacing-2xl;

  .action-card {
    text-align: center;
    border-radius: $radius-lg;
    transition: transform $transition-base ease;

    &:hover {
      transform: translateY(-4px);
    }

    .card-content {
      padding: $spacing-lg 0;

      h3 {
        font-size: $font-size-xl;
        font-weight: $font-weight-semibold;
        color: $text-primary;
        margin: $spacing-md 0 $spacing-sm;
      }

      p {
        font-size: $font-size-base;
        color: $text-secondary;
      }
    }
  }
}

.progress-card {
  border-radius: $radius-lg;

  .card-header {
    h2 {
      font-size: $font-size-xl;
      font-weight: $font-weight-semibold;
      color: $text-primary;
    }
  }

  .progress-stats {
    .stat-item {
      text-align: center;
      padding: $spacing-lg 0;

      .stat-value {
        font-size: $font-size-3xl;
        font-weight: $font-weight-bold;
        color: $primary-color;
        margin-bottom: $spacing-sm;
      }

      .stat-label {
        font-size: $font-size-base;
        color: $text-secondary;
      }
    }
  }
}

@media (max-width: $container-md) {
  .header-content {
    padding: 0 $spacing-lg;
  }

  .main-content {
    padding: $spacing-xl $spacing-lg;
  }

  .welcome-section {
    h1 {
      font-size: $font-size-2xl;
    }
  }

  .quick-actions {
    :deep(.el-col) {
      margin-bottom: $spacing-lg;
    }
  }
}
</style>
