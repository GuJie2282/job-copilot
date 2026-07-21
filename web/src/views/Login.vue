<template>
  <div class="auth">
    <!-- 左：品牌叙事区 -->
    <aside class="auth__brand">
      <div class="brand-inner">
        <div class="brand-logo">
          <span class="brand-mark">求</span>
          <span class="brand-name">求职 Copilot</span>
        </div>
        <h1 class="brand-thesis">把模糊的求职，<br />变成清晰的清单。</h1>
        <p class="brand-sub">AI 求职教练 · 从画像到 Offer 的全链路陪伴</p>
        <ol class="brand-flow">
          <li><span class="num">01</span> 建立画像</li>
          <li><span class="num">02</span> JD 匹配</li>
          <li><span class="num">03</span> 简历优化</li>
          <li><span class="num">04</span> 模拟面试</li>
        </ol>
      </div>
    </aside>

    <!-- 右：表单区 -->
    <main class="auth__panel">
      <div class="panel-inner">
        <header class="panel-head">
          <h2>欢迎回来</h2>
          <p>登录后继续你的求职进度</p>
        </header>

        <el-form
          ref="loginFormRef"
          :model="loginForm"
          :rules="loginRules"
          class="auth-form"
          size="large"
          label-position="top"
        >
          <el-form-item prop="email" label="邮箱">
            <el-input
              v-model="loginForm.email"
              placeholder="you@example.com"
              :disabled="isLoading"
            />
          </el-form-item>

          <el-form-item prop="password" label="密码">
            <el-input
              v-model="loginForm.password"
              type="password"
              placeholder="至少 6 位"
              show-password
              :disabled="isLoading"
              @keyup.enter="handleLogin"
            />
          </el-form-item>

          <div class="form-row">
            <el-checkbox v-model="rememberMe" :disabled="isLoading">记住我</el-checkbox>
          </div>

          <el-button
            type="primary"
            class="submit"
            :loading="isLoading"
            :disabled="isLoading"
            @click="handleLogin"
          >
            {{ isLoading ? '登录中…' : '登录' }}
          </el-button>
        </el-form>

        <p class="switch">
          还没有账号？<el-link type="primary" :underline="false" @click="goToRegister">立即注册</el-link>
        </p>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { ElMessage, type FormInstance, type FormRules } from 'element-plus';
import { useUserStore } from '@/stores/user';
import type { LoginCredentials } from '@/types/user';

// 路由
const router = useRouter();
const route = useRoute();

// 状态管理
const userStore = useUserStore();

// 表单引用与加载状态
const loginFormRef = ref<FormInstance>();
const isLoading = ref(false);
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

    // 把「记住我」勾选状态一起传给 store → API（决定 Refresh Token 有效期）
    await userStore.login({ ...loginForm, rememberMe: rememberMe.value });

    ElMessage.success('登录成功');

    // 跳转到目标页面或首页
    const redirect = (route.query['redirect'] as string) || '/';
    router.push(redirect);
  } catch (error) {
    console.error('登录失败:', error);
    // ElMessage 已在拦截器中处理
  } finally {
    isLoading.value = false;
  }
};

/**
 * 跳转到注册页面
 */
const goToRegister = (): void => {
  router.push('/register');
};
</script>

<style scoped lang="scss">
.form-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-lg;
}

.submit {
  width: 100%;
  height: 48px;
  font-size: $font-size-base;
  font-weight: $font-weight-semibold;
}

.switch {
  text-align: center;
  margin-top: $spacing-xl;
  font-size: $font-size-sm;
  color: $text-secondary;
}
</style>
