/**
 * 统一请求封装
 * - 自动注入 JWT Token
 * - 401 自动跳登录页
 * - 统一错误处理
 */
import Taro from '@tarojs/taro'
import { API_V1 } from '../config'

interface RequestOptions {
  url: string          // 相对路径，如 '/users/me'
  method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'
  data?: any
  header?: Record<string, string>
  showError?: boolean  // 默认 true，是否自动 Toast 错误
}

interface ApiResponse<T = any> {
  data: T
  statusCode: number
}

// Token 存取
export function getToken(): string {
  return Taro.getStorageSync('token') || ''
}

export function setToken(token: string) {
  Taro.setStorageSync('token', token)
}

export function clearToken() {
  Taro.removeStorageSync('token')
}

export function isLoggedIn(): boolean {
  return !!getToken()
}

// 跳转登录页
export function redirectToLogin() {
  clearToken()
  Taro.redirectTo({ url: '/pages/login/index' })
}

// 核心请求函数
export async function request<T = any>(options: RequestOptions): Promise<T> {
  const { url, method = 'GET', data, header = {}, showError = true } = options
  const token = getToken()

  const fullUrl = url.startsWith('http') ? url : `${API_V1}${url}`

  const headers: Record<string, string> = {
    ...header,
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  // 如果没有指定 Content-Type 且不是 FormData，默认 JSON
  if (!headers['Content-Type'] && method !== 'GET') {
    headers['Content-Type'] = 'application/json'
  }

  try {
    const res = await Taro.request({
      url: fullUrl,
      method,
      data,
      header: headers,
    })

    if (res.statusCode === 401) {
      redirectToLogin()
      throw new Error('未登录或 Token 已过期')
    }

    if (res.statusCode >= 400) {
      const detail = res.data?.detail || `请求失败 (${res.statusCode})`
      if (showError) {
        Taro.showToast({ title: detail, icon: 'none', duration: 2000 })
      }
      throw new Error(detail)
    }

    return res.data as T
  } catch (err: any) {
    // 网络错误
    if (err.errMsg && err.errMsg.includes('request:fail')) {
      if (showError) {
        Taro.showToast({ title: '网络连接失败', icon: 'none' })
      }
    }
    throw err
  }
}

// 快捷方法
export const api = {
  get: <T = any>(url: string, data?: any) =>
    request<T>({ url, method: 'GET', data }),

  post: <T = any>(url: string, data?: any, header?: Record<string, string>) =>
    request<T>({ url, method: 'POST', data, header }),

  patch: <T = any>(url: string, data?: any) =>
    request<T>({ url, method: 'PATCH', data }),

  put: <T = any>(url: string, data?: any) =>
    request<T>({ url, method: 'PUT', data }),

  delete: <T = any>(url: string) =>
    request<T>({ url, method: 'DELETE' }),
}

export default api
