"use client";

import { useState, useEffect } from 'react';
import { login as apiLogin, register as apiRegister, logout as apiLogout, getAccessToken, fetchUserInfo, UserInfo as AuthUserInfo } from '@/lib/auth-api';

export interface UserInfo extends AuthUserInfo {}

interface AuthState {
  isLoading: boolean;
  error: string | null;
  user: UserInfo | null;
  login: (usernameOrEmail: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

export const useAuth = (): AuthState => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [user, setUser] = useState<UserInfo | null>(null);

  // 初始化时从 localStorage 加载用户信息
  useEffect(() => {
    const loadUser = () => {
      try {
        const userStr = localStorage.getItem('user');
        if (userStr) {
          setUser(JSON.parse(userStr));
        }
      } catch (err) {
        console.error('加载用户信息失败:', err);
        setUser(null);
      }
    };

    loadUser();
  }, []);

  const login = async (usernameOrEmail: string, password: string): Promise<void> => {
    setIsLoading(true);
    setError(null);

    try {
      // 使用 apiLogin 函数
      await apiLogin({
        username_or_email: usernameOrEmail,
        password
      });

      // 获取完整的用户信息
      const userInfo = await fetchUserInfo();
      localStorage.setItem('user', JSON.stringify(userInfo));
      setUser(userInfo);
    } catch (err) {
      setError(err instanceof Error ? err.message : '登录失败');
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (username: string, email: string, password: string): Promise<void> => {
    setIsLoading(true);
    setError(null);

    try {
      // 调用实际的注册 API
      await apiRegister({
        username,
        email,
        password
      });

      // 获取完整的用户信息
      const userInfo = await fetchUserInfo();
      localStorage.setItem('user', JSON.stringify(userInfo));
      setUser(userInfo);
    } catch (err) {
      setError(err instanceof Error ? err.message : '注册失败');
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async (): Promise<void> => {
    try {
      // 调用实际的登出 API
      await apiLogout();
    } catch (err) {
      console.error('登出失败:', err);
      // 即使登出请求失败，也清除本地存储的令牌
    } finally {
      // 清除用户信息
      localStorage.removeItem('user');
      setUser(null);
    }
  };

  return {
    isLoading,
    error,
    user,
    login,
    register,
    logout
  };
};