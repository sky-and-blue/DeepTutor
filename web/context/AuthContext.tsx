// 认证上下文
// 实现全局认证状态管理和相关方法

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import {
  UserRegisterData,
  UserLoginData,
  AuthResponse,
  UserInfo,
  login,
  register,
  logout,
  getAccessToken,
  isAuthenticated as checkIsAuthenticated,
  refreshToken,
  fetchUserInfo
} from '../lib/auth-api';

// 认证上下文类型定义
interface AuthContextType {
  // 认证状态
  isAuthenticated: boolean;
  user: UserInfo | null;
  loading: boolean;
  error: string | null;
  
  // 认证方法
  login: (userData: UserLoginData) => Promise<void>;
  register: (userData: UserRegisterData) => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
}

// 创建认证上下文
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// 认证提供者组件属性
interface AuthProviderProps {
  children: ReactNode;
}

// 认证提供者组件
export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  // 状态定义
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [user, setUser] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // 检查认证状态
  const checkAuth = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // 检查本地存储中的令牌
      const token = getAccessToken();
      if (token) {
        setIsAuthenticated(true);
        // 获取用户信息
        try {
          const userInfo = await fetchUserInfo();
          setUser(userInfo);
        } catch (err) {
          // 如果获取用户信息失败，清除认证状态
          setIsAuthenticated(false);
          setUser(null);
        }
      } else {
        setIsAuthenticated(false);
        setUser(null);
      }
    } catch (err) {
      setError('认证检查失败');
      setIsAuthenticated(false);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  // 登录方法
  const handleLogin = async (userData: UserLoginData) => {
    try {
      setLoading(true);
      setError(null);
      
      await login(userData);
      setIsAuthenticated(true);
      // 获取并设置用户信息
      const userInfo = await fetchUserInfo();
      setUser(userInfo);
    } catch (err) {
      setError(err instanceof Error ? err.message : '登录失败');
      setIsAuthenticated(false);
      setUser(null);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // 注册方法
  const handleRegister = async (userData: UserRegisterData) => {
    try {
      setLoading(true);
      setError(null);
      
      await register(userData);
      setIsAuthenticated(true);
      // 获取并设置用户信息
      const userInfo = await fetchUserInfo();
      setUser(userInfo);
    } catch (err) {
      setError(err instanceof Error ? err.message : '注册失败');
      setIsAuthenticated(false);
      setUser(null);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // 登出方法
  const handleLogout = async () => {
    try {
      setLoading(true);
      await logout();
      setIsAuthenticated(false);
      setUser(null);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : '登出失败');
    } finally {
      setLoading(false);
    }
  };

  // 组件挂载时检查认证状态
  useEffect(() => {
    checkAuth();
  }, []);

  // 上下文值
  const contextValue: AuthContextType = {
    isAuthenticated,
    user,
    loading,
    error,
    login: handleLogin,
    register: handleRegister,
    logout: handleLogout,
    checkAuth
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};

// 自定义钩子，方便在组件中使用认证上下文
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// 导出认证上下文（用于特殊情况）
export { AuthContext };
