// API 配置
// 开发时用 localhost，生产替换为真实域名
export const API_BASE = process.env.NODE_ENV === 'production'
  ? 'https://api.petafu.com'  // TODO: 替换为真实域名
  : 'http://localhost:8000'

export const API_V1 = `${API_BASE}/api/v1`
