/**
 * 认证相关 API
 */
import client from './client';
import type { LoginCredentials, RegisterData, LoginResponse } from '@/types';

/**
 * 错误响应接口（后端统一格式）
 */
interface ErrorResponse {
  code: string;
  message: string;
  details?: Record<string, unknown>;
  action?: string;
}

/**
 * API 错误类
 */
export class AuthApiError extends Error {
  code: string;
  action?: string;

  constructor(message: string, code: string, action?: string) {
    super(message);
    this.name = 'AuthApiError';
    this.code = code;
    this.action = action;
  }
}

/**
 * 检查响应是否为错误响应
 */
function isErrorResponse(data: unknown): data is ErrorResponse {
  return (
    typeof data === 'object' &&
    data !== null &&
    'code' in data &&
    'message' in data
  );
}

export const authApi = {
  /**
   * 用户登录
   */
  async login(credentials: LoginCredentials): Promise<LoginResponse> {
    try {
      // 转换字段名：前端驼峰 rememberMe → 后端下划线 remember_me
      const { rememberMe, ...rest } = credentials;
      const payload = {
        ...rest,
        remember_me: rememberMe ?? false
      };
      return await client.post('/auth/login', payload);
    } catch (error: unknown) {
      throw this._handleError(error);
    }
  },

  /**
   * 用户注册
   */
  async register(data: RegisterData): Promise<LoginResponse> {
    try {
      // 转换字段名：前端驼峰 → 后端下划线
      const { confirmPassword, ...rest } = data;  // 移除 confirmPassword
      const payload = {
        ...rest,
        verification_code: data.verificationCode  // 驼峰转下划线
      };
      return await client.post('/auth/register', payload);
    } catch (error: unknown) {
      throw this._handleError(error);
    }
  },

  /**
   * 发送验证码
   */
  async sendVerificationCode(email: string): Promise<any> {
    try {
      return await client.post('/auth/send-code', { email });
    } catch (error: unknown) {
      throw this._handleError(error);
    }
  },

  /**
   * 验证验证码
   */
  async verifyCode(email: string, code: string): Promise<any> {
    try {
      return await client.post('/auth/verify-code', { email, code });
    } catch (error: unknown) {
      throw this._handleError(error);
    }
  },

  /**
   * 退出登录
   */
  async logout(): Promise<any> {
    try {
      return await client.post('/auth/logout');
    } catch (error: unknown) {
      throw this._handleError(error);
    }
  },

  /**
   * 刷新 Token
   */
  async refreshToken(refreshToken: string): Promise<{ token: string; refresh_token: string }> {
    try {
      return await client.post('/auth/refresh', { refreshToken });
    } catch (error: unknown) {
      throw this._handleError(error);
    }
  },

  /**
   * 处理 API 错误
   */
  _handleError(error: unknown): AuthApiError {
    // Axios error
    if (error && typeof error === 'object' && 'response' in error) {
      const response = error.response as { data?: unknown };
      if (response.data && isErrorResponse(response.data)) {
        const errorData = response.data;
        return new AuthApiError(
          errorData.message,
          errorData.code,
          errorData.action
        );
      }
    }

    // 未知错误
    return new AuthApiError(
      '未知错误，请稍后重试',
      'UNKNOWN_ERROR'
    );
  }
};