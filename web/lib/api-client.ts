// API 客户端实现
// 基于 fetch 的 API 客户端，支持请求拦截器和响应拦截器

import { apiUrl } from './api';
import { getAccessToken, clearTokens, refreshToken } from './auth-api';

/**
 * API 请求选项
 */
export interface ApiRequestOptions extends RequestInit {
  /**
   * 是否需要认证
   * @default true
   */
  requiresAuth?: boolean;
  /**
   * 是否自动处理 401 错误
   * @default true
   */
  handle401?: boolean;
}

/**
 * API 客户端类
 */
export class ApiClient {
  /**
   * 发送 API 请求
   * @param path - API 路径
   * @param options - 请求选项
   * @returns 响应数据
   */
  async request<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
    const {
      requiresAuth = true,
      handle401 = true,
      headers = {},
      ...restOptions
    } = options;

    // 构建请求头
    const requestHeaders = this.buildHeaders(headers, requiresAuth);

    // 发送请求
    const response = await fetch(apiUrl(path), {
      ...restOptions,
      headers: requestHeaders,
    });

    // 处理响应
    return this.handleResponse<T>(response, handle401);
  }

  /**
   * 构建请求头
   * @param headers - 自定义请求头
   * @param requiresAuth - 是否需要认证
   * @returns 构建后的请求头
   */
  private buildHeaders(headers: HeadersInit, requiresAuth: boolean): HeadersInit {
    // 转换 headers 为对象格式
    let newHeaders: Record<string, string> = {};
    
    if (headers instanceof Headers) {
      headers.forEach((value, key) => {
        newHeaders[key] = value;
      });
    } else if (Array.isArray(headers)) {
      headers.forEach(([key, value]) => {
        newHeaders[key] = value;
      });
    } else if (headers) {
      newHeaders = { ...headers };
    }

    // 如果需要认证，添加 Authorization 头
    if (requiresAuth) {
      const token = getAccessToken();
      if (token) {
        newHeaders['Authorization'] = `Bearer ${token}`;
      }
    }

    // 确保 Content-Type 头
    if (!newHeaders['Content-Type'] && !newHeaders['content-type']) {
      newHeaders['Content-Type'] = 'application/json';
    }

    return newHeaders;
  }

  /**
   * 处理响应
   * @param response - 响应对象
   * @param handle401 - 是否自动处理 401 错误
   * @returns 响应数据
   */
  private async handleResponse<T>(response: Response, handle401: boolean): Promise<T> {
    // 检查响应状态
    if (!response.ok) {
      // 处理 401 错误
      if (response.status === 401 && handle401) {
        await this.handle401Error();
      }

      // 解析错误数据
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `请求失败: ${response.status}`);
    }

    // 解析响应数据
    const data = await response.json().catch(() => ({}));
    return data as T;
  }

  /**
   * 处理 401 错误
   */
  private async handle401Error(): Promise<void> {
    try {
      // 尝试刷新令牌
      await refreshToken();
    } catch (error) {
      // 刷新令牌失败，清除本地存储的令牌并跳转到登录页面
      clearTokens();
      window.location.href = '/auth/login';
    }
  }

  /**
   * 发送 GET 请求
   * @param path - API 路径
   * @param options - 请求选项
   * @returns 响应数据
   */
  async get<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
    return this.request<T>(path, {
      ...options,
      method: 'GET',
    });
  }

  /**
   * 发送 POST 请求
   * @param path - API 路径
   * @param data - 请求数据
   * @param options - 请求选项
   * @returns 响应数据
   */
  async post<T>(path: string, data: any, options: ApiRequestOptions = {}): Promise<T> {
    return this.request<T>(path, {
      ...options,
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /**
   * 发送 PUT 请求
   * @param path - API 路径
   * @param data - 请求数据
   * @param options - 请求选项
   * @returns 响应数据
   */
  async put<T>(path: string, data: any, options: ApiRequestOptions = {}): Promise<T> {
    return this.request<T>(path, {
      ...options,
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  /**
   * 发送 DELETE 请求
   * @param path - API 路径
   * @param options - 请求选项
   * @returns 响应数据
   */
  async delete<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
    return this.request<T>(path, {
      ...options,
      method: 'DELETE',
    });
  }
}

// 导出 API 客户端实例
export const apiClient = new ApiClient();

// 导出与现有 API 调用方式一致的接口
export * from './api';
