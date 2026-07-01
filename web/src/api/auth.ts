/**
 * 认证相关 API
 */
import client from './client';
import type { ApiResponse, LoginCredentials, RegisterData, LoginResponse } from '@/types';

export const authApi = {
  /**
   * 用户登录
   */
  async login(credentials: LoginCredentials): Promise<ApiResponse<LoginResponse>> {
    return client.post('/auth/login', credentials);
  },

  /**
   * 用户注册
   */
  async register(data: RegisterData): Promise<ApiResponse<LoginResponse>> {
    return client.post('/auth/register', data);
  },

  /**
   * 发送验证码
   */
  async sendVerificationCode(email: string): Promise<ApiResponse<void>> {
    return client.post('/auth/send-code', { email });
  },

  /**
   * 验证验证码
   */
  async verifyCode(email: string, code: string): Promise<ApiResponse<boolean>> {
    return client.post('/auth/verify-code', { email, code });
  },

  /**
   * 退出登录
   */
  async logout(): Promise<ApiResponse<void>> {
    return client.post('/auth/logout');
  },

  /**
   * 刷新 Token
   */
  async refreshToken(refreshToken: string): Promise<ApiResponse<{ token: string; refreshToken: string }>> {
    return client.post('/auth/refresh', { refreshToken });
  }
};
