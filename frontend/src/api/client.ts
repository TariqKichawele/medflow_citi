import { API_BASE_URL, TOKEN_KEY } from '../constants'
import type {
  AnalyticsSummary,
  Equipment,
  EquipmentWrite,
  Hospital,
  HospitalWrite,
  ListQuery,
  Paged,
  ReportingLineItem,
  ServiceReport,
  RoleRecord,
  User,
  UserWrite,
  WorkOrder,
  WorkOrderWrite,
} from './types'

function token(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

function queryString(params: ListQuery): string {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    search.set(key, String(value))
  })
  const qs = search.toString()
  return qs ? `?${qs}` : ''
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json()
    if (body && typeof body === 'object' && 'detail' in body) {
      const detail = (body as { detail: unknown }).detail
      if (typeof detail === 'string') return detail
      if (Array.isArray(detail)) {
        return detail
          .map((item) => {
            if (item && typeof item === 'object' && 'msg' in item) {
              return String((item as { msg: unknown }).msg)
            }
            return JSON.stringify(item)
          })
          .join('; ')
      }
    }
  } catch {
    /* ignore parse errors */
  }
  return response.statusText || `Request failed (${response.status})`
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  const auth = token()
  if (auth) headers.set('Authorization', `Bearer ${auth}`)
  if (init.body && !(init.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers })
  if (response.status === 204) return undefined as T
  if (!response.ok) {
    throw new Error(await errorMessage(response))
  }
  return (await response.json()) as T
}

export function resolveFileUrl(fileUrl: string): string {
  if (fileUrl.startsWith('http://') || fileUrl.startsWith('https://')) return fileUrl
  return `${API_BASE_URL}${fileUrl}`
}

export const api = {
  login(email: string, password: string) {
    return request<{ access_token: string; token_type: string }>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
  },
  me() {
    return request<User>('/api/v1/auth/me')
  },
  roles: {
    list: () => request<RoleRecord[]>('/api/v1/roles'),
    permissions: () => request<{ permissions: string[] }>('/api/v1/roles/permissions'),
    create: (payload: { name: string; description: string; permissions: string[] }) =>
      request<RoleRecord>('/api/v1/roles', { method: 'POST', body: JSON.stringify(payload) }),
  },
  users: {
    list: (params: ListQuery = {}) => request<Paged<User>>(`/api/v1/users${queryString(params)}`),
    create: (payload: UserWrite) =>
      request<User>('/api/v1/users', { method: 'POST', body: JSON.stringify(payload) }),
    update: (id: number, payload: Partial<UserWrite>) =>
      request<User>(`/api/v1/users/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
    deactivate: (id: number) => request<void>(`/api/v1/users/${id}`, { method: 'DELETE' }),
  },
  hospitals: {
    list: (params: ListQuery = {}) =>
      request<Paged<Hospital>>(`/api/v1/hospitals${queryString(params)}`),
    create: (payload: HospitalWrite) =>
      request<Hospital>('/api/v1/hospitals', { method: 'POST', body: JSON.stringify(payload) }),
    update: (id: number, payload: Partial<HospitalWrite>) =>
      request<Hospital>(`/api/v1/hospitals/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(payload),
      }),
    remove: (id: number) => request<void>(`/api/v1/hospitals/${id}`, { method: 'DELETE' }),
  },
  equipment: {
    list: (params: ListQuery = {}) =>
      request<Paged<Equipment>>(`/api/v1/equipment${queryString(params)}`),
    create: (payload: EquipmentWrite) =>
      request<Equipment>('/api/v1/equipment', { method: 'POST', body: JSON.stringify(payload) }),
    update: (id: number, payload: Partial<EquipmentWrite>) =>
      request<Equipment>(`/api/v1/equipment/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(payload),
      }),
    remove: (id: number) => request<void>(`/api/v1/equipment/${id}`, { method: 'DELETE' }),
  },
  workOrders: {
    list: (params: ListQuery = {}) =>
      request<Paged<WorkOrder>>(`/api/v1/work-orders${queryString(params)}`),
    create: (payload: WorkOrderWrite) =>
      request<WorkOrder>('/api/v1/work-orders', { method: 'POST', body: JSON.stringify(payload) }),
    update: (id: number, payload: Partial<WorkOrderWrite>) =>
      request<WorkOrder>(`/api/v1/work-orders/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(payload),
      }),
    remove: (id: number) => request<void>(`/api/v1/work-orders/${id}`, { method: 'DELETE' }),
    reports: (id: number) =>
      request<Paged<ServiceReport>>(`/api/v1/work-orders/${id}/reports?page_size=100`),
    uploadReport: (id: number, file: File, notes: string) => {
      const body = new FormData()
      body.append('file', file)
      if (notes) body.append('notes', notes)
      return request<ServiceReport>(`/api/v1/work-orders/${id}/reports`, { method: 'POST', body })
    },
  },
  analytics: {
    summary: () => request<AnalyticsSummary>('/api/v1/analytics/summary'),
    reportingLines: (supervisorId?: number) =>
      request<{ items: ReportingLineItem[] }>(
        `/api/v1/analytics/reporting-lines${supervisorId ? `?supervisor_id=${supervisorId}` : ''}`,
      ),
  },
}

export async function fetchAll<T>(
  list: (params: ListQuery) => Promise<Paged<T>>,
  extra: ListQuery = {},
): Promise<T[]> {
  const first = await list({ ...extra, page: 1, page_size: 100 })
  const items = [...first.items]
  const pages = Math.ceil(first.total / first.page_size) || 1
  for (let page = 2; page <= pages; page += 1) {
    const next = await list({ ...extra, page, page_size: 100 })
    items.push(...next.items)
  }
  return items
}
