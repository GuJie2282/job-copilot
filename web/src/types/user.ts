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
  rememberMe?: boolean;  // 记住我（勾选则后端发 30 天长期 Refresh Token）
}

/**
 * 注册数据
 */
export interface RegisterData {
  name: string;
  email: string;
  password: string;
  confirmPassword?: string;  // 确认密码（仅前端验证，不提交到后端）
  phone?: string;
  verificationCode: string;
}

/**
 * 登录响应
 */
export interface LoginResponse {
  user: User;
  token: string;
  refresh_token: string;
}

/**
 * 刷新 Token 请求
 */
export interface RefreshTokenRequest {
  refreshToken: string;
}
