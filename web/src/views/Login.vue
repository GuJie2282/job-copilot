<template>
  <div class="login-container">
    <div class="login-box">
      <!-- Logo 和标题 -->
      <div class="login-header">
        <div class="logo">
          <el-icon :size="48" color="#2563eb">
            <UserFilled />
          </el-icon>
        </div>
        <h1 class="title">求职 Copilot</h1>
        <p class="subtitle">你的私人求职教练</p>
      </div>

      <!-- 登录表单 -->
      <el-form
        ref="loginFormRef"
        :model="loginForm"
        :rules="loginRules"
        class="login-form"
        size="large"
      >
        <el-form-item prop="email">
          <el-input
            v-model="loginForm.email"
            placeholder="邮箱地址"
            prefix-icon="Message"
            :disabled="isLoading"
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="密码"
            prefix-icon="Lock"
            show-password
            :disabled="isLoading"
            @keyup.enter="handleLogin"
          />
        </el-form-item>

        <div class="form-options">
          <el-checkbox v-model="rememberMe" :disabled="isLoading">记住我</el-checkbox>
          <el-link type="primary">忘记密码？</el-link>
        </div>

        <el-form-item>
          <el-button
            type="primary"
            class="login-button"
            :loading="isLoading"
            :disabled="isLoading"
            @click="handleLogin"
          >
            {{ isLoading ? '登录中...' : '登录' }}
          </el-button>
        </el-form-item>

        <!-- 第三方登录 -->
        <div class="divider">
          <span>或使用第三方登录</span>
        </div>

        <div class="social-login">
          <el-button
            class="social-button wechat"
            :disabled="isLoading"
            @click="handleWechatLogin"
          >
            <el-icon><ChatDotSquare /></el-icon>
            <span>微信登录</span>
          </el-button>
        </div>

        <!-- 注册链接 -->
        <div class="register-link">
          还没有账号？
          <el-link type="primary" @click="goToRegister">立即注册</el-link>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { ElMessage, type FormInstance, type FormRules } from 'element-plus';
import { UserFilled, Lock, Message, ChatDotSquare } from '@element-plus/icons-vue';
import { useUserStore } from '@/stores/user';
import type { LoginCredentials } from '@/types/user';

// 路由
const router = useRouter();
const route = useRoute();

// 状态管理
const userStore = useUserStore();

// 表单引用
const loginFormRef = ref<FormInstance>();

// 加载状态
const isLoading = ref(false);

// 记住我
const rememberMe = ref(false);

// 登录表单数据
const loginForm = reactive<LoginCredentials>({
  email: '',
  password: ''
});

// 表单验证规则
const loginRules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少 6 位', trigger: 'blur' }
  ]
};

/**
 * 处理登录
 */
const handleLogin = async (): Promise<void> => {
  if (!loginFormRef.value) return;

  try {
    const valid = await loginFormRef.value.validate();
    if (!valid) return;

    isLoading.value = true;

    await userStore.login(loginForm);

    ElMessage.success('登录成功');

    // 跳转到目标页面或首页
    const redirect = (route.query.redirect as string) || '/';
    router.push(redirect);
  } catch (error) {
    console.error('登录失败:', error);
    // ElMessage 已在拦截器中处理
  } finally {
    isLoading.value = false;
  }
};

/**
 * 微信登录（暂未实现）
 */
const handleWechatLogin = (): void => {
  ElMessage.info('微信登录功能即将上线');
};

/**
 * 跳转到注册页面
 */
const goToRegister = (): void => {
  router.push('/register');
};
</script>

<style scoped lang="scss">
@import '@/styles/variables.scss';

.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: $spacing-lg;
}

.login-box {
  width: 100%;
  max-width: 420px;
  background: $bg-white;
  border-radius: $radius-xl;
  box-shadow: $shadow-lg;
  padding: $spacing-2xl;
}

.login-header {
  text-align: center;
  margin-bottom: $spacing-2xl;
}

.logo {
  margin-bottom: $spacing-md;
}

.title {
  font-size: $font-size-3xl;
  font-weight: $font-weight-bold;
  color: $text-primary;
  margin-bottom: $spacing-sm;
}

.subtitle {
  font-size: $font-size-lg;
  color: $text-secondary;
}

.login-form {
  :deep(.el-form-item) {
    margin-bottom: $spacing-lg;
  }

  :deep(.el-input__wrapper) {
    border-radius: $radius-md;
    padding: $spacing-sm $spacing-md;
  }
}

.form-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-lg;
}

.login-button {
  width: 100%;
  height: 48px;
  font-size: $font-size-lg;
  font-weight: $font-weight-semibold;
  border-radius: $radius-md;
}

.divider {
  display: flex;
  align-items: center;
  text-align: center;
  margin: $spacing-xl 0;

  &::before,
  &::after {
    content: '';
    flex: 1;
    border-bottom: 1px solid $border-color;
  }

  span {
    padding: 0 $spacing-md;
    font-size: $font-size-sm;
    color: $text-secondary;
  }
}

.social-login {
  display: flex;
  gap: $spacing-md;
}

.social-button {
  flex: 1;
  height: 44px;
  border-radius: $radius-md;

  &.wechat {
    border-color: #07c160;
    color: #07c160;

    &:hover {
      background: #f0fdf4;
      border-color: #07c160;
    }
  }

  :deep(.el-icon) {
    margin-right: $spacing-xs;
  }
}

.register-link {
  text-align: center;
  margin-top: $spacing-xl;
  font-size: $font-size-base;
  color: $text-secondary;
}

@media (max-width: $container-sm) {
  .login-container {
    padding: $spacing-md;
  }

  .login-box {
    padding: $spacing-xl;
  }

  .title {
    font-size: $font-size-2xl;
  }
}
</style>
