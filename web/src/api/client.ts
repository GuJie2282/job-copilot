/**
 * Axios 客户端配置
 */
import axios, { type AxiosInstance, type AxiosError, type InternalAxiosRequestConfig } from 'axios';
import type { ApiResponse, ApiError } from '@/types/api';
import { ElMessage } from 'element-plus';
import { authApi } from './auth';

// 创建 axios 实例
const client: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// 正在刷新 Token 的标志（防止并发刷新）
let isRefreshing = false;
// 等待刷新完成的队列
let refreshSubscribers: ((token: string) => void)[] = [];

/**
 * 添加订阅者到队列
 */
function subscribeTokenRefresh(callback: (token: string) => void) {
  refreshSubscribers.push(callback);
}

/**
 * 通知所有订阅者 Token 已刷新
 */
function onTokenRefreshed(token: string) {
  refreshSubscribers.forEach(callback => callback(token));
  refreshSubscribers = [];
}

// 请求拦截器 - 添加 token
client.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器 - 处理错误和 Token 刷新
client.interceptors.response.use(
  (response) => {
    return response.data;
  },
  async (error: AxiosError) => {
    const apiError: ApiError = {
      code: error.response?.status || 500,
      message: (error.response?.data as any)?.message || '请求失败',
      details: error.response?.data
    };

    const originalRequest = error.config as InternalAxiosRequestConfig & { _isRetry?: boolean };

    // 处理 401 错误 - Token 可能过期
    if (error.response?.status === 401 && !originalRequest._isRetry) {
      // 标记请求已重试，防止死循环
      originalRequest._isRetry = true;

      const refreshToken = localStorage.getItem('refreshToken');

      if (!refreshToken) {
        // 没有 Refresh Token，直接跳转登录
        ElMessage.error('登录已过期，请重新登录');
        localStorage.removeItem('token');
        localStorage.removeItem('refreshToken');
        window.location.href = '/login';
        return Promise.reject(apiError);
      }

      // 如果正在刷新，等待刷新完成
      if (isRefreshing) {
        return new Promise((resolve) => {
          subscribeTokenRefresh((token: string) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            resolve(client(originalRequest));
          });
        });
      }

      // 开始刷新 Token
      isRefreshing = true;

      try {
        // 调用刷新 Token 接口
        const response = await authApi.refreshToken(refreshToken);
        const newToken = response.data.token;
        const newRefreshToken = response.data.refreshToken;

        // 更新 localStorage
        localStorage.setItem('token', newToken);
        localStorage.setItem('refreshToken', newRefreshToken);

        // 通知所有等待的请求
        onTokenRefreshed(newToken);

        // 重试原始请求
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return client(originalRequest);
      } catch (refreshError) {
        // 刷新失败，清除 Token 并跳转登录
        console.error('Token 刷新失败:', refreshError);
        ElMessage.error('登录已过期，请重新登录');
        localStorage.removeItem('token');
        localStorage.removeItem('refreshToken');
        window.location.href = '/login';
        return Promise.reject(apiError);
      } finally {
        isRefreshing = false;
      }
    }

    // 处理其他错误状态码
    if (error.response?.status === 403) {
      ElMessage.error('没有权限访问');
    } else if (error.response?.status === 500) {
      ElMessage.error('服务器错误，请稍后重试');
    } else if (error.response?.status !== 401) {
      // 401 已在上面处理，这里跳过
      ElMessage.error(apiError.message);
    }

    return Promise.reject(apiError);
  }
);

export default client;
