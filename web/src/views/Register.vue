<template>
  <div class="register-container">
    <div class="register-box">
      <!-- Logo 和标题 -->
      <div class="register-header">
        <div class="logo">
          <el-icon :size="48" color="#2563eb">
            <UserFilled />
          </el-icon>
        </div>
        <h1 class="title">求职 Copilot</h1>
        <p class="subtitle">开始你的求职之旅</p>
      </div>

      <!-- 注册表单 -->
      <el-form
        ref="registerFormRef"
        :model="registerForm"
        :rules="registerRules"
        class="register-form"
        size="large"
      >
        <el-form-item prop="name">
          <el-input
            v-model="registerForm.name"
            placeholder="姓名"
            prefix-icon="User"
            :disabled="isLoading"
          />
        </el-form-item>

        <el-form-item prop="email">
          <el-input
            v-model="registerForm.email"
            placeholder="邮箱地址"
            prefix-icon="Message"
            :disabled="isLoading"
          />
        </el-form-item>

        <el-form-item prop="phone">
          <el-input
            v-model="registerForm.phone"
            placeholder="手机号（可选）"
            prefix-icon="Phone"
            :disabled="isLoading"
          />
        </el-form-item>

        <el-form-item prop="verificationCode">
          <div class="verification-code-wrapper">
            <el-input
              v-model="registerForm.verificationCode"
              placeholder="验证码"
              prefix-icon="Key"
              :disabled="isLoading"
            />
            <el-button
              type="primary"
              :disabled="isCodeSending || countdown > 0 || !isEmailValid"
              :loading="isCodeSending"
              @click="handleSendCode"
            >
              {{ countdown > 0 ? `${countdown}秒后重试` : '获取验证码' }}
            </el-button>
          </div>
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="registerForm.password"
            type="password"
            placeholder="密码（至少6位）"
            prefix-icon="Lock"
            show-password
            :disabled="isLoading"
          />
        </el-form-item>

        <el-form-item prop="confirmPassword">
          <el-input
            v-model="confirmPassword"
            type="password"
            placeholder="确认密码"
            prefix-icon="Lock"
            show-password
            :disabled="isLoading"
            @keyup.enter="handleRegister"
          />
        </el-form-item>

        <!-- 服务条款 -->
        <el-form-item prop="agreement">
          <el-checkbox v-model="agreedToTerms" :disabled="isLoading">
            我已阅读并同意
            <el-link type="primary">《用户协议》</el-link>
            和
            <el-link type="primary">《隐私政策》</el-link>
          </el-checkbox>
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            class="register-button"
            :loading="isLoading"
            :disabled="isLoading || !agreedToTerms"
            @click="handleRegister"
          >
            {{ isLoading ? '注册中...' : '注册' }}
          </el-button>
        </el-form-item>

        <!-- 登录链接 -->
        <div class="login-link">
          已有账号？
          <el-link type="primary" @click="goToLogin">立即登录</el-link>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, type FormInstance, type FormRules } from 'element-plus';
import { UserFilled, User, Lock, Message, Phone, Key } from '@element-plus/icons-vue';
import { useUserStore } from '@/stores/user';
import { authApi } from '@/api/auth';
import type { RegisterData } from '@/types/user';

// 路由
const router = useRouter();

// 状态管理
const userStore = useUserStore();

// 表单引用
const registerFormRef = ref<FormInstance>();

// 加载状态
const isLoading = ref(false);
const isCodeSending = ref(false);

// 倒计时
const countdown = ref(0);

// 确认密码
const confirmPassword = ref('');

// 同意条款
const agreedToTerms = ref(false);

// 注册表单数据
const registerForm = reactive<RegisterData>({
  name: '',
  email: '',
  phone: '',
  password: '',
  verificationCode: ''
});

// 验证邮箱格式是否有效
const isEmailValid = computed(() => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(registerForm.email);
});

// 自定义验证：确认密码
const validateConfirmPassword = (_rule: unknown, value: string, callback: (error?: Error) => void): void => {
  if (value !== registerForm.password) {
    callback(new Error('两次输入的密码不一致'));
  } else {
    callback();
  }
};

// 表单验证规则
const registerRules: FormRules = {
  name: [
    { required: true, message: '请输入姓名', trigger: 'blur' },
    { min: 2, max: 20, message: '姓名长度应为 2-20 个字符', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  phone: [
    {
      pattern: /^1[3-9]\d{9}$/,
      message: '请输入正确的手机号',
      trigger: 'blur'
    }
  ],
  verificationCode: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { len: 6, message: '验证码应为 6 位数字', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少 6 位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ],
  agreement: [
    {
      validator: (_rule: unknown, _value: unknown, callback: (error?: Error) => void) => {
        if (!agreedToTerms.value) {
          callback(new Error('请阅读并同意用户协议和隐私政策'));
        } else {
          callback();
        }
      },
      trigger: 'change'
    }
  ]
};

/**
 * 发送验证码
 */
const handleSendCode = async (): Promise<void> => {
  if (!isEmailValid.value) {
    ElMessage.warning('请先输入有效的邮箱地址');
    return;
  }

  try {
    isCodeSending.value = true;
    await authApi.sendVerificationCode(registerForm.email);
    ElMessage.success('验证码已发送到您的邮箱');

    // 开始倒计时
    countdown.value = 60;
    const timer = setInterval(() => {
      countdown.value--;
      if (countdown.value <= 0) {
        clearInterval(timer);
      }
    }, 1000);
  } catch (error) {
    console.error('发送验证码失败:', error);
  } finally {
    isCodeSending.value = false;
  }
};

/**
 * 处理注册
 */
const handleRegister = async (): Promise<void> => {
  if (!registerFormRef.value) return;

  try {
    const valid = await registerFormRef.value.validate();
    if (!valid) return;

    isLoading.value = true;

    await userStore.register(registerForm);

    ElMessage.success('注册成功');

    // 跳转到首页
    router.push('/');
  } catch (error) {
    console.error('注册失败:', error);
  } finally {
    isLoading.value = false;
  }
};

/**
 * 跳转到登录页面
 */
const goToLogin = (): void => {
  router.push('/login');
};
</script>

<style scoped lang="scss">
@import '@/styles/variables.scss';

.register-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: $spacing-lg;
}

.register-box {
  width: 100%;
  max-width: 460px;
  background: $bg-white;
  border-radius: $radius-xl;
  box-shadow: $shadow-lg;
  padding: $spacing-2xl;
}

.register-header {
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

.register-form {
  :deep(.el-form-item) {
    margin-bottom: $spacing-lg;
  }

  :deep(.el-input__wrapper) {
    border-radius: $radius-md;
    padding: $spacing-sm $spacing-md;
  }
}

.verification-code-wrapper {
  display: flex;
  gap: $spacing-sm;
  width: 100%;

  .el-input {
    flex: 1;
  }

  .el-button {
    flex-shrink: 0;
  }
}

.register-button {
  width: 100%;
  height: 48px;
  font-size: $font-size-lg;
  font-weight: $font-weight-semibold;
  border-radius: $radius-md;
}

.login-link {
  text-align: center;
  margin-top: $spacing-xl;
  font-size: $font-size-base;
  color: $text-secondary;
}

@media (max-width: $container-sm) {
  .register-container {
    padding: $spacing-md;
  }

  .register-box {
    padding: $spacing-xl;
  }

  .title {
    font-size: $font-size-2xl;
  }

  .verification-code-wrapper {
    flex-direction: column;

    .el-button {
      width: 100%;
    }
  }
}
</style>
