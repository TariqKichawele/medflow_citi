export type Role = string

export type RoleRecord = {
  id: number
  name: string
  description: string
  permissions: string[]
}
export type EquipmentStatus = 'available' | 'in_use' | 'maintenance' | 'offline'
export type WorkOrderStatus = 'pending' | 'in_progress' | 'completed' | 'failed'
export type Priority = 'low' | 'medium' | 'critical'

export type Paged<T> = {
  items: T[]
  total: number
  page: number
  page_size: number
}

export type User = {
  id: number
  email: string
  full_name: string
  role: Role
  facility_id: number | null
  reports_to_id: number | null
  is_active: boolean
  permissions?: string[]
}

export type UserWrite = {
  email: string
  full_name: string
  role: Role
  password?: string
  facility_id: number | null
  reports_to_id: number | null
  is_active: boolean
}

export type Hospital = {
  id: number
  name: string
  location_region: string
  capacity: number
  supervisor_id: number | null
}

export type HospitalWrite = {
  name: string
  location_region: string
  capacity: number
  supervisor_id: number | null
}

export type Equipment = {
  id: number
  serial_number: string
  model: string
  status: EquipmentStatus
  charge_level: number
  facility_id: number
}

export type EquipmentWrite = {
  serial_number: string
  model: string
  status: EquipmentStatus
  charge_level: number
  facility_id: number
}

export type WorkOrder = {
  id: number
  title: string
  priority: Priority
  status: WorkOrderStatus
  equipment_id: number
  technician_id: number
}

export type WorkOrderWrite = {
  title: string
  priority: Priority
  status: WorkOrderStatus
  equipment_id: number
  technician_id: number
}

export type ServiceReport = {
  id: number
  work_order_id: number
  file_url: string
  notes: string | null
  created_at: string
  uploaded_by_id: number
}

export type LowChargeItem = {
  id: number
  serial_number: string
  model: string
  status: string
  charge_level: number
  facility_id: number
  hospital_name: string
}

export type ColocationItem = {
  equipment_id: number
  serial_number: string
  model: string
  equipment_facility_id: number
  equipment_hospital: string
  technician_id: number
  technician_name: string
  technician_facility_id: number | null
  work_order_id: number
}

export type ReliabilityItem = {
  model: string
  completed: number
  failed: number
  completion_rate: number
}

export type MaintenanceFlagItem = {
  hospital_id: number
  hospital_name: string
  total_devices: number
  maintenance_devices: number
  maintenance_ratio: number
}

export type ReportingLineItem = {
  supervisor_id: number
  supervisor_name: string
  technicians_with_active_orders: number
}

export type AnalyticsSummary = {
  low_charge: LowChargeItem[]
  colocation_discrepancies: { count: number; items: ColocationItem[] }
  reliability: ReliabilityItem[]
  maintenance_flags: MaintenanceFlagItem[]
  reporting_lines: ReportingLineItem[]
}

export type ListQuery = {
  page?: number
  page_size?: number
  search?: string
  status?: string
  role?: string
  facility_id?: number
  technician_id?: number
  equipment_id?: number
  sort_by?: string
  sort_dir?: 'asc' | 'desc'
}
