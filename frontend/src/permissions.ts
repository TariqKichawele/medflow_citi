// Permission names match backend app/permissions.py. Which role holds a
// permission comes from GET /api/v1/auth/me, not from this file.
export const Permission = {
  hospitalRead: 'hospital:read',
  hospitalWrite: 'hospital:write',
  equipmentRead: 'equipment:read',
  equipmentReadAssigned: 'equipment:read_assigned',
  equipmentWrite: 'equipment:write',
  workOrderRead: 'work_order:read',
  workOrderReadAssigned: 'work_order:read_assigned',
  workOrderWrite: 'work_order:write',
  workOrderStatus: 'work_order:status',
  reportRead: 'report:read',
  reportUpload: 'report:upload',
  analyticsRead: 'analytics:read',
  userRead: 'user:read',
  userManage: 'user:manage',
  roleRead: 'role:read',
  roleManage: 'role:manage',
} as const
