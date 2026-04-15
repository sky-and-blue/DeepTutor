import { NextRequest, NextResponse } from 'next/server';

// 定义需要保护的路由路径
const protectedPaths = [
  '/', // 根路径（workspace 主页）
  '/playground',
  '/guide',
  '/co-writer',
  '/agents',
  '/agents/*',
];

// 定义不需要保护的路由路径
const publicPaths = [
  '/auth/login',
  '/auth/register',
  '/api', // API 路径（由后端处理）
  '/_next', // Next.js 内部路径
  '/favicon.ico',
];

// 检查路径是否需要保护
function isProtectedPath(pathname: string): boolean {
  // 首先检查是否是公共路径
  for (const publicPath of publicPaths) {
    if (publicPath.endsWith('*')) {
      const basePath = publicPath.slice(0, -1);
      if (pathname.startsWith(basePath)) {
        return false;
      }
    } else if (pathname === publicPath) {
      return false;
    }
  }

  // 然后检查是否是受保护路径
  for (const protectedPath of protectedPaths) {
    if (protectedPath.endsWith('*')) {
      const basePath = protectedPath.slice(0, -1);
      if (pathname.startsWith(basePath)) {
        return true;
      }
    } else if (pathname === protectedPath) {
      return true;
    }
  }

  // 默认返回 false（公共路径）
  return false;
}

// 检查是否已登录
function isAuthenticated(request: NextRequest): boolean {
  // 从 cookie 中获取令牌
  // 注意：在中间件中，我们只能访问 cookie，不能访问 localStorage
  const token = request.cookies.get('auth_access_token')?.value;
  return !!token;
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // 检查路径是否需要保护
  if (isProtectedPath(pathname)) {
    // 检查是否已登录
    if (!isAuthenticated(request)) {
      // 未登录，重定向到登录页面
      const loginUrl = new URL('/auth/login', request.url);
      // 保存原始请求的 URL，登录后可以重定向回
      loginUrl.searchParams.set('redirect', pathname);
      return NextResponse.redirect(loginUrl);
    }
  }

  // 已登录或路径不需要保护，继续处理请求
  return NextResponse.next();
}

// 配置中间件适用的路径
export const config = {
  matcher: [
    /*
     * 匹配所有请求路径，除了：
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
};
