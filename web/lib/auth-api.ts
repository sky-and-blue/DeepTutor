// 认证 API 集成
// 实现与后端认证相关的 API 调用和令牌管理

import { apiUrl } from './api';

// 认证相关的类型定义

/**
 * 用户注册数据
 */
export interface UserRegisterData {
  username: string;
  email: string;
  password: string;
}

/**
 * 用户登录数据
 */
export interface UserLoginData {
  username_or_email: string;
  password: string;
}

/**
 * 认证响应数据
 */
export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

/**
 * 用户信息
 */
export interface UserInfo {
  id: number;
  username: string;
  email: string;
  created_at: string;
  // 其他用户信息字段
}

// 令牌存储键名
const ACCESS_TOKEN_KEY = 'auth_access_token';
const REFRESH_TOKEN_KEY = 'auth_refresh_token';

/**
 * 设置 cookie
 * @param name cookie 名称
 * @param value cookie 值
 * @param days 过期天数
 */
function setCookie(name: string, value: string, days: number = 7): void {
  if (typeof document !== 'undefined') {
    const expires = new Date();
    expires.setTime(expires.getTime() + days * 24 * 60 * 60 * 1000);
    let cookieString = `${name}=${value};expires=${expires.toUTCString()};path=/;SameSite=Strict`;
    if (location.protocol === 'https:') {
      cookieString += ';Secure';
    }
    document.cookie = cookieString;
  }
}

/**
 * 获取 cookie
 * @param name cookie 名称
 * @returns cookie 值，如果不存在则返回 null
 */
function getCookie(name: string): string | null {
  if (typeof document !== 'undefined') {
    const cookieValue = document.cookie
      .split('; ')
      .find(row => row.startsWith(`${name}=`))
      ?.split('=')[1];
    return cookieValue || null;
  }
  return null;
}

/**
 * 删除 cookie
 * @param name cookie 名称
 */
function deleteCookie(name: string): void {
  if (typeof document !== 'undefined') {
    document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/;`;
  }
}

/**
 * 从 localStorage 获取访问令牌
 * @returns 访问令牌，如果不存在则返回 null
 */
export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

/**
 * 从 localStorage 获取刷新令牌
 * @returns 刷新令牌，如果不存在则返回 null
 */
export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

/**
 * 存储令牌到 localStorage 和 cookie
 * @param tokens 认证响应对象
 */
export function setTokens(tokens: AuthResponse): void {
  // 存储到 localStorage
  localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
  localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
  
  // 存储到 cookie（用于中间件访问）
  setCookie(ACCESS_TOKEN_KEY, tokens.access_token, 1); // 1天过期
  setCookie(REFRESH_TOKEN_KEY, tokens.refresh_token, 7); // 7天过期
}

/**
 * 清除 localStorage 和 cookie 中的令牌
 */
export function clearTokens(): void {
  // 清除 localStorage
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  
  // 清除 cookie
  deleteCookie(ACCESS_TOKEN_KEY);
  deleteCookie(REFRESH_TOKEN_KEY);
}

/**
 * 检查是否已登录
 * @returns 是否已登录
 */
export function isAuthenticated(): boolean {
  return getAccessToken() !== null;
}

/**
 * 注册新用户
 * @param userData 用户注册数据
 * @returns 认证响应
 */
export async function register(userData: UserRegisterData): Promise<AuthResponse> {
  try {
    const response = await fetch(apiUrl('/api/v1/auth/register'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(userData),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      let errorMessage = '注册失败';
      
      if (errorData.detail) {
        if (typeof errorData.detail === 'string') {
          errorMessage = errorData.detail;
        } else if (Array.isArray(errorData.detail)) {
          errorMessage = errorData.detail.map((item: any) => item.msg || item).join('; ');
        } else if (typeof errorData.detail === 'object') {
          errorMessage = JSON.stringify(errorData.detail);
        }
      }
      
      throw new Error(errorMessage);
    }

    const data = await response.json();
    setTokens(data);
    return data;
  } catch (error) {
    console.error('注册失败:', error);
    throw error;
  }
}

/**
 * 用户登录
 * @param userData 用户登录数据
 * @returns 认证响应
 */
export async function login(userData: UserLoginData): Promise<AuthResponse> {
  try {
    const response = await fetch(apiUrl('/api/v1/auth/login'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(userData),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      let errorMessage = '登录失败';
      
      if (errorData.detail) {
        if (typeof errorData.detail === 'string') {
          errorMessage = errorData.detail;
        } else if (Array.isArray(errorData.detail)) {
          errorMessage = errorData.detail.map((item: any) => item.msg || item).join('; ');
        } else if (typeof errorData.detail === 'object') {
          errorMessage = JSON.stringify(errorData.detail);
        }
      }
      
      throw new Error(errorMessage);
    }

    const data = await response.json();
    setTokens(data);
    return data;
  } catch (error) {
    console.error('登录失败:', error);
    throw error;
  }
}

/**
 * 刷新访问令牌
 * @returns 新的认证响应
 */
export async function refreshToken(): Promise<AuthResponse> {
  try {
    const refreshToken = getRefreshToken();
    if (!refreshToken) {
      throw new Error('刷新令牌不存在');
    }

    const response = await fetch(apiUrl('/api/v1/auth/refresh'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      if (response.status === 401) {
        // 刷新令牌失效，清除本地存储的令牌
        clearTokens();
      }
      const errorData = await response.json().catch(() => ({}));
      let errorMessage = '令牌刷新失败';
      
      if (errorData.detail) {
        if (typeof errorData.detail === 'string') {
          errorMessage = errorData.detail;
        } else if (Array.isArray(errorData.detail)) {
          errorMessage = errorData.detail.map((item: any) => item.msg || item).join('; ');
        } else if (typeof errorData.detail === 'object') {
          errorMessage = JSON.stringify(errorData.detail);
        }
      }
      
      throw new Error(errorMessage);
    }

    const data = await response.json();
    setTokens(data);
    return data;
  } catch (error) {
    console.error('令牌刷新失败:', error);
    throw error;
  }
}

/**
 * 获取当前用户信息
 * @returns 用户信息
 */
export async function fetchUserInfo(): Promise<UserInfo> {
  try {
    const accessToken = getAccessToken();
    if (!accessToken) {
      throw new Error('未登录');
    }

    const response = await fetch(apiUrl('/api/v1/auth/me'), {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      let errorMessage = '获取用户信息失败';
      
      if (errorData.detail) {
        if (typeof errorData.detail === 'string') {
          errorMessage = errorData.detail;
        } else if (Array.isArray(errorData.detail)) {
          errorMessage = errorData.detail.map((item: any) => item.msg || item).join('; ');
        } else if (typeof errorData.detail === 'object') {
          errorMessage = JSON.stringify(errorData.detail);
        }
      }
      
      throw new Error(errorMessage);
    }

    return await response.json();
  } catch (error) {
    console.error('获取用户信息失败:', error);
    throw error;
  }
}

/**
 * 用户登出
 */
export async function logout(): Promise<void> {
  try {
    const accessToken = getAccessToken();
    if (accessToken) {
      await fetch(apiUrl('/api/v1/auth/logout'), {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
        },
      });
    }
  } catch (error) {
    console.error('登出失败:', error);
    // 即使登出请求失败，也清除本地存储的令牌
  } finally {
    clearTokens();
  }
}
