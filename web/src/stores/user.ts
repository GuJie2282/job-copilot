/**
 * 用户状态管理
 */
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { User, LoginCredentials, RegisterData } from '@/types/user';
import { authApi } from '@/api/auth';

export const useUserStore = defineStore('user', () => {
  // 状态
  const user = ref<User | null>(null);
  const token = ref<string | null>(localStorage.getItem('token'));
  const isLoading = ref(false);

  // 计算属性
  const isLoggedIn = computed(() => !!token.value && !!user.value);
  const userName = computed(() => user.value?.name || '');
  const userEmail = computed(() => user.value?.email || '');

  /**
   * 登录
   */
  async function login(credentials: LoginCredentials): Promise<void> {
    isLoading.value = true;
    try {
      const response = await authApi.login(credentials);
      user.value = response.data.user;
      token.value = response.data.token;
      localStorage.setItem('token', response.data.token);

      // 如果有 refresh token，也保存
      if (response.data.refreshToken) {
        localStorage.setItem('refreshToken', response.data.refreshToken);
      }
    } finally {
      isLoading.value = false;
    }
  }

  /**
   * 注册
   */
  async function register(data: RegisterData): Promise<void> {
    isLoading.value = true;
    try {
      const response = await authApi.register(data);
      user.value = response.data.user;
      token.value = response.data.token;
      localStorage.setItem('token', response.data.token);

      if (response.data.refreshToken) {
        localStorage.setItem('refreshToken', response.data.refreshToken);
      }
    } finally {
      isLoading.value = false;
    }
  }

  /**
   * 退出登录
   */
  async function logout(): Promise<void> {
    try {
      await authApi.logout();
    } catch (error) {
      console.error('退出登录失败:', error);
    } finally {
      user.value = null;
      token.value = null;
      localStorage.removeItem('token');
      localStorage.removeItem('refreshToken');
    }
  }

  /**
   * 初始化用户状态
   */
  function initUserState(): void {
    const savedToken = localStorage.getItem('token');
    if (savedToken) {
      token.value = savedToken;
    }
  }

  /**
   * 刷新 Token（手动刷新）
   * 通常由 Axios 拦截器自动调用，此方法供手动触发
   */
  async function refreshTokens(): Promise<void> {
    const refreshToken = localStorage.getItem('refreshToken');
    if (!refreshToken) {
      throw new Error('没有 Refresh Token');
    }

    try {
      const response = await authApi.refreshToken(refreshToken);
      token.value = response.data.token;
      localStorage.setItem('token', response.data.token);
      localStorage.setItem('refreshToken', response.data.refreshToken);
    } catch (error) {
      // 刷新失败，清除状态
      user.value = null;
      token.value = null;
      localStorage.removeItem('token');
      localStorage.removeItem('refreshToken');
      throw error;
    }
  }

  return {
    // 状态
    user,
    token,
    isLoading,
    // 计算属性
    isLoggedIn,
    userName,
    userEmail,
    // 方法
    login,
    register,
    logout,
    initUserState,
    refreshTokens
  };
});
