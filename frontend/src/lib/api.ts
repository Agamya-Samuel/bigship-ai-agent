import axios from 'axios'
import type { LoginRequest, LoginResponse, SessionListResponse, ChatResponse, StreamEvent } from '../types'

const API_BASE = import.meta.env.VITE_API_URL || '/'

export const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && err.config?.url !== '/auth/login') {
      localStorage.removeItem('access_token')
      localStorage.removeItem('account_id')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export async function login(req: LoginRequest): Promise<LoginResponse> {
  const { data } = await api.post('/auth/login', req)
  return data
}

export async function getMe(): Promise<{ account_id: string; user_name: string }> {
  const { data } = await api.get('/auth/me')
  return data
}

export async function logout(): Promise<void> {
  await api.post('/auth/logout')
}

export async function getSessions(): Promise<SessionListResponse> {
  const { data } = await api.get('/sessions')
  return data
}

export async function createSession(label?: string): Promise<{ thread_id: string }> {
  const { data } = await api.post('/sessions', { label: label || '' })
  return data
}

export async function deleteSession(threadId: string): Promise<void> {
  await api.delete(`/sessions/${encodeURIComponent(threadId)}`)
}

export async function sendChat(threadId: string, message: string): Promise<ChatResponse> {
  const { data } = await api.post('/chat', { thread_id: threadId, message })
  return data
}

export async function streamChat(
  threadId: string,
  message: string,
  onEvent: (ev: StreamEvent) => void
): Promise<void> {
  const token = localStorage.getItem('access_token')
  const resp = await fetch(`${API_BASE}/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ thread_id: threadId, message }),
  })
  if (!resp.ok || !resp.body) {
    throw new Error(`Stream failed with status ${resp.status}`)
  }
  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    let sep: number
    while ((sep = buffer.indexOf('\n\n')) !== -1) {
      const frame = buffer.slice(0, sep)
      buffer = buffer.slice(sep + 2)
      for (const line of frame.split('\n')) {
        if (line.startsWith('data: ')) {
          onEvent(JSON.parse(line.slice(6)) as StreamEvent)
        }
      }
    }
  }
}

export async function getChatHistory(threadId: string) {
  const { data } = await api.get(`/chat/history/${encodeURIComponent(threadId)}`)
  return data
}

export async function getProfile() {
  const { data } = await api.get('/api/profile')
  return data
}

export async function getWarehouses(params: Record<string, unknown>) {
  const { data } = await api.get('/api/warehouses', { params })
  return data
}

export async function saveWarehouse(payload: Record<string, unknown>) {
  const { data } = await api.post('/api/warehouses', payload)
  return data
}

export async function updateWarehouse(warehouseId: string, payload: Record<string, unknown>) {
  const { data } = await api.put(`/api/warehouses/${encodeURIComponent(warehouseId)}`, payload)
  return data
}

export async function getOrders(params: Record<string, unknown>) {
  const { data } = await api.get('/api/orders', { params })
  return data
}

export async function getOrderDetail(orderId: string) {
  const { data } = await api.get(`/api/orders/${encodeURIComponent(orderId)}`)
  return data
}

export async function cancelOrder(orderId: string) {
  const { data } = await api.post(`/api/orders/${encodeURIComponent(orderId)}/cancel`)
  return data
}

export async function trackOrder(orderId: string) {
  const { data } = await api.get(`/api/orders/${encodeURIComponent(orderId)}/track`)
  return data
}

export async function getPaymentModes(segmentType: string) {
  const { data } = await api.get('/api/rate-calculator/payment-modes', { params: { segment_type: segmentType } })
  return data
}

export async function getPackageTypes() {
  const { data } = await api.get('/api/rate-calculator/package-types')
  return data
}

export async function calculateRate(payload: Record<string, unknown>) {
  const { data } = await api.post('/api/rate-calculator/calculate', payload)
  return data
}
