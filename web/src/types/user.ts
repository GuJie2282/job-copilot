/**
 * 用户相关类型定义
 */

/**
 * 用户基础信息
 */
export interface User {
  id: string;
  name: string;
  email: string;
  phone?: string;
  avatar?: string;
  createdAt: string;
}

/**
 * 登录凭证
 */
export interface LoginCredentials {
  email: string;
  password: string;
}

/**
 * 注册数据
 */
export interface RegisterData {
  name: string;
  email: string;
  password: string;
  phone?: string;
  verificationCode: string;
}

/**
 * 登录响应
 */
export interface LoginResponse {
  user: User;
  token: string;
  refreshToken?: string;
}

/**
 * 刷新 Token 请求
 */
export interface RefreshTokenRequest {
  refreshToken: string;
}
