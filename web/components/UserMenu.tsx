"use client";

import { useState } from 'react';
import { User, LogOut } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { useRouter } from 'next/navigation';

interface UserMenuProps {
  className?: string;
}

export function UserMenu({ className = '' }: UserMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const { logout, user } = useAuth();
  const router = useRouter();

  const handleLogout = async () => {
    try {
      await logout();
      router.push('/auth/login');
    } catch (error) {
      console.error('登出失败:', error);
    }
  };

  // 获取显示的用户名
  const displayName = user?.username || user?.email || '用户';

  return (
    <div className={`relative ${className}`}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 rounded-lg px-3 py-2 text-[13.5px] text-[var(--muted-foreground)] transition-colors hover:bg-[var(--background)]/50 hover:text-[var(--foreground)]"
      >
        <User size={16} strokeWidth={1.5} />
        <span>{displayName}</span>
      </button>
      
      {isOpen && (
        <div className="absolute bottom-full right-0 mb-2 w-48 rounded-lg bg-[var(--secondary)] border border-[var(--border)] shadow-lg py-1 z-50">
          <button
            onClick={handleLogout}
            className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-[13px] text-[var(--muted-foreground)] transition-colors hover:bg-[var(--background)]/50 hover:text-[var(--foreground)]"
          >
            <LogOut size={14} strokeWidth={1.5} />
            <span>登出</span>
          </button>
        </div>
      )}
    </div>
  );
}
