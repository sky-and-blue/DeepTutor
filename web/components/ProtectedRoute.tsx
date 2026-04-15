"use client";

import React, { ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';

// 路由保护组件属性
interface ProtectedRouteProps {
  children: ReactNode;
}

/**
 * 路由保护组件
 * 用于保护需要登录才能访问的页面
 * - 未登录用户访问时重定向到登录页面
 * - 已登录用户正常访问
 * - 处理加载状态
 */
export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const router = useRouter();
  const { isLoading, user } = useAuth();

  // 处理加载状态
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-[var(--primary)] mx-auto"></div>
          <p className="mt-4 text-[var(--muted-foreground)]">加载中...</p>
        </div>
      </div>
    );
  }

  // 未登录用户重定向到登录页面
  if (!user) {
    router.push('/auth/login');
    return null;
  }

  // 已登录用户正常访问
  return <>{children}</>;
}
