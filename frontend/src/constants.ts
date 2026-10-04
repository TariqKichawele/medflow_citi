export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

export const TOKEN_KEY = 'medflow_token'

export const ROLE_CLINICAL_ADMIN = 'clinical_admin'
export const ROLE_FIELD_TECHNICIAN = 'field_technician'
export const ROLE_AUDITOR = 'auditor'

export const EQUIPMENT_STATUSES = ['available', 'in_use', 'maintenance', 'offline'] as const
export const WORK_ORDER_STATUSES = ['pending', 'in_progress', 'completed', 'failed'] as const
export const PRIORITIES = ['low', 'medium', 'critical'] as const
export const ROLES = [ROLE_CLINICAL_ADMIN, ROLE_FIELD_TECHNICIAN, ROLE_AUDITOR] as const
export const DEMO_PASSWORD = 'Medflow123!'

