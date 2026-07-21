<template>
  <div class="auth">
    <!-- 左：品牌叙事区（与登录页一致） -->
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
          <h2>创建账号</h2>
          <p>注册后，开启你的求职诊断</p>
        </header>

        <el-form
          ref="registerFormRef"
          :model="registerForm"
          :rules="registerRules"
          class="auth-form"
          size="large"
          label-position="top"
        >
          <el-form-item prop="name" label="姓名">
            <el-input
              v-model="registerForm.name"
              placeholder="2–20 个字符"
              :disabled="isLoading"
            />
          </el-form-item>

          <el-form-item prop="email" label="邮箱">
            <el-input
              v-model="registerForm.email"
              placeholder="you@example.com"
              :disabled="isLoading"
            />
          </el-form-item>

          <el-form-item prop="phone" label="手机号（可选）">
            <el-input
              v-model="registerForm.phone"
              placeholder="选填，便于后续功能通知"
              :disabled="isLoading"
            />
          </el-form-item>

          <el-form-item prop="verificationCode" label="邮箱验证码">
            <div class="code-row">
              <el-input
                v-model="registerForm.verificationCode"
                placeholder="6 位数字"
                :disabled="isLoading"
              />
              <el-button
                type="primary"
                plain
                class="send-btn"
                :disabled="isCodeSending || countdown > 0 || !isEmailValid"
                :loading="isCodeSending"
                @click="handleSendCode"
              >
                {{ countdown > 0 ? `${countdown}s 后重试` : '获取验证码' }}
              </el-button>
            </div>
          </el-form-item>

          <el-form-item prop="password" label="密码">
            <el-input
              v-model="registerForm.password"
              type="password"
              placeholder="至少 6 位"
              show-password
              :disabled="isLoading"
            />
          </el-form-item>

          <el-form-item prop="confirmPassword" label="确认密码">
            <el-input
              v-model="registerForm.confirmPassword"
              type="password"
              placeholder="再输入一次"
              show-password
              :disabled="isLoading"
              @keyup.enter="handleRegister"
            />
          </el-form-item>

          <el-form-item prop="agreement" class="agreement">
            <el-checkbox v-model="agreedToTerms" :disabled="isLoading">
              我已阅读并同意
              <el-link type="primary" :underline="false">《用户协议》</el-link>
              和
              <el-link type="primary" :underline="false">《隐私政策》</el-link>
            </el-checkbox>
          </el-form-item>

          <el-button
            type="primary"
            class="submit"
            :loading="isLoading"
            :disabled="isLoading || !agreedToTerms"
            @click="handleRegister"
          >
            {{ isLoading ? '注册中…' : '注册' }}
          </el-button>
        </el-form>

        <p class="switch">
          已有账号？<el-link type="primary" :underline="false" @click="goToLogin">立即登录</el-link>
        </p>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, type FormInstance, type FormRules } from 'element-plus';
import { useUserStore } from '@/stores/user';
import { authApi, AuthApiError } from '@/api/auth';
import type { RegisterData } from '@/types/user';

// 路由
const router = useRouter();

// 状态管理
const userStore = useUserStore();

// 表单引用与加载状态
const registerFormRef = ref<FormInstance>();
const isLoading = ref(false);
const isCodeSending = ref(false);

// 倒计时
const countdown = ref(0);

// 同意条款
const agreedToTerms = ref(false);

// 注册表单数据
const registerForm = reactive<RegisterData>({
  name: '',
  email: '',
  phone: '',
  password: '',
  confirmPassword: '',
  verificationCode: ''
});

// 验证邮箱格式是否有效（用于「获取验证码」按钮的启用判断）
const isEmailValid = computed(() => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(registerForm.email);
});

// 自定义验证：确认密码
const validateConfirmPassword = (_rule: unknown, value: string, callback: (error?: Error) => void): void => {
  if (!value) {
    callback();
    return;
  }
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
    ElMessage.success('验证码已发送到你的邮箱');

    // 开始 60 秒倒计时
    countdown.value = 60;
    const timer = setInterval(() => {
      countdown.value--;
      if (countdown.value <= 0) {
        clearInterval(timer);
      }
    }, 1000);
  } catch (error) {
    if (error instanceof AuthApiError) {
      ElMessage.error(error.message);
      if (error.action === 'wait') {
        ElMessage.warning('发送过于频繁，请稍后再试');
      }
    } else {
      ElMessage.error('发送验证码失败，请稍后重试');
    }
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
    router.push('/');
  } catch (error) {
    if (error instanceof AuthApiError) {
      ElMessage.error(error.message);

      if (error.action === 'login') {
        // 邮箱已存在，提示登录
        ElMessage({
          message: '该邮箱已注册，即将跳转到登录页面',
          type: 'info',
          duration: 2000,
          onClose: () => {
            router.push('/login');
          }
        });
      } else if (error.action === 'resend_code') {
        ElMessage.warning('验证码有问题，请重新获取');
      } else if (error.action === 'fix_password') {
        ElMessage.warning('请检查密码格式');
      }
    } else {
      ElMessage.error('注册失败，请稍后重试');
    }
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
.code-row {
  display: flex;
  gap: $spacing-sm;
  width: 100%;

  :deep(.el-input) {
    flex: 1;
  }

  .send-btn {
    flex-shrink: 0;
  }
}

.agreement {
  :deep(.el-checkbox__label) {
    font-size: $font-size-sm;
    color: $text-secondary;
    line-height: $line-height-normal;
  }
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

@media (max-width: 480px) {
  .code-row {
    flex-direction: column;

    .send-btn {
      width: 100%;
    }
  }
}
</style>
