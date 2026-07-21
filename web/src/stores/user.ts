/**
 * 用户状态管理
 */
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { User, LoginCredentials, RegisterData } from '@/types/user';
import { authApi } from '@/api/auth';

export const useUserStore = defineStore('user', () => {
  // 从 localStorage 恢复用户：路由守卫在 App.vue onMounted(initUserState) 之前执行，
  // 必须在 store 创建时就恢复 user，否则刷新页面会被守卫误判未登录、踢回 /login。
  function loadSavedUser(): User | null {
    try {
      const s = localStorage.getItem('user');
      return s ? (JSON.parse(s) as User) : null;
    } catch {
      return null;
    }
  }

  // 状态
  const user = ref<User | null>(loadSavedUser());
  const token = ref<string | null>(localStorage.getItem('token'));
  const isLoading = ref(false);

  // 计算属性
  const isLoggedIn = computed(() => !!token.value && !!user.value);
  const userName = computed(() => user.value?.name || '');
  const userEmail = computed(() => user.value?.email || '');
  const userId = computed(() => user.value?.id || '');

  /**
   * 登录
   */
  async function login(credentials: LoginCredentials): Promise<void> {
    isLoading.value = true;
    try {
      const response = await authApi.login(credentials);
      user.value = response.user;
      token.value = response.token;
      localStorage.setItem('token', response.token);
      // 持久化用户信息：刷新页面后连同 token 一起恢复，保持登录态（配合「记住我」的 refresh token 有效期）
      localStorage.setItem('user', JSON.stringify(response.user));

      // 如果有 refresh token，也保存
      if (response.refresh_token) {
        localStorage.setItem('refreshToken', response.refresh_token);
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
      user.value = response.user;
      token.value = response.token;
      localStorage.setItem('token', response.token);
      // 持久化用户信息：刷新页面后连同 token 一起恢复，保持登录态（配合「记住我」的 refresh token 有效期）
      localStorage.setItem('user', JSON.stringify(response.user));

      if (response.refresh_token) {
        localStorage.setItem('refreshToken', response.refresh_token);
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
      localStorage.removeItem('user');
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
    // 恢复用户信息：isLoggedIn = !!token && !!user，若 user 不恢复会被路由守卫误判为未登录
    const savedUser = localStorage.getItem('user');
    if (savedUser) {
      try {
        user.value = JSON.parse(savedUser);
      } catch {
        // user 数据损坏则清除，避免脏数据
        localStorage.removeItem('user');
      }
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
      token.value = response.token;
      localStorage.setItem('token', response.token);
      localStorage.setItem('refreshToken', response.refresh_token);
    } catch (error) {
      // 刷新失败，清除状态
      user.value = null;
      token.value = null;
      localStorage.removeItem('token');
      localStorage.removeItem('refreshToken');
      localStorage.removeItem('user');
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
    userId,
    // 方法
    login,
    register,
    logout,
    initUserState,
    refreshTokens
  };
});
