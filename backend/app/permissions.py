"""Named permissions and the built-in role grants.

Permissions live in this module and are referenced by the enum everywhere else.
Role grants are rows in ``roles`` / ``role_permissions``, not branches in endpoint
code. A table is used instead of a dict so an admin can introduce a role by
writing data: no endpoint changes, and a fresh database gets the three built-in
roles from seed and from the migration. ``get_current_user`` loads the caller's
role and its grants on every request, so editing a role applies on the next
call without reissuing tokens.

There is no separate audit-history resource. The auditor's read grants are the
operational records that role could already read.
"""

from enum import Enum

from app.constants import ROLE_AUDITOR, ROLE_CLINICAL_ADMIN, ROLE_FIELD_TECHNICIAN


class Permission(str, Enum):
    HOSPITAL_READ = "hospital:read"
    HOSPITAL_WRITE = "hospital:write"
    EQUIPMENT_READ = "equipment:read"
    EQUIPMENT_READ_ASSIGNED = "equipment:read_assigned"
    EQUIPMENT_WRITE = "equipment:write"
    WORK_ORDER_READ = "work_order:read"
    WORK_ORDER_READ_ASSIGNED = "work_order:read_assigned"
    WORK_ORDER_WRITE = "work_order:write"
    WORK_ORDER_STATUS = "work_order:status"
    REPORT_READ = "report:read"
    REPORT_UPLOAD = "report:upload"
    ANALYTICS_READ = "analytics:read"
    USER_READ = "user:read"
    USER_MANAGE = "user:manage"
    ROLE_READ = "role:read"
    ROLE_MANAGE = "role:manage"
    HEALTH_READ = "health:read"


class BuiltinRole:
    def __init__(self, description: str, permissions: frozenset[Permission]) -> None:
        self.description = description
        self.permissions = permissions


_ADMIN = frozenset(
    {
        Permission.HOSPITAL_READ,
        Permission.HOSPITAL_WRITE,
        Permission.EQUIPMENT_READ,
        Permission.EQUIPMENT_WRITE,
        Permission.WORK_ORDER_READ,
        Permission.WORK_ORDER_WRITE,
        Permission.WORK_ORDER_STATUS,
        Permission.REPORT_READ,
        Permission.REPORT_UPLOAD,
        Permission.ANALYTICS_READ,
        Permission.USER_READ,
        Permission.USER_MANAGE,
        Permission.ROLE_READ,
        Permission.ROLE_MANAGE,
        Permission.HEALTH_READ,
    }
)

_TECHNICIAN = frozenset(
    {
        Permission.HOSPITAL_READ,
        Permission.EQUIPMENT_READ_ASSIGNED,
        Permission.WORK_ORDER_READ_ASSIGNED,
        Permission.WORK_ORDER_STATUS,
        Permission.REPORT_READ,
        Permission.REPORT_UPLOAD,
        Permission.ANALYTICS_READ,
    }
)

_AUDITOR = frozenset(
    {
        Permission.HOSPITAL_READ,
        Permission.EQUIPMENT_READ,
        Permission.WORK_ORDER_READ,
        Permission.REPORT_READ,
        Permission.ANALYTICS_READ,
        Permission.USER_READ,
    }
)

BUILTIN_ROLES: dict[str, BuiltinRole] = {
    ROLE_CLINICAL_ADMIN: BuiltinRole(
        "Full access to hospitals, equipment, work orders, users, and roles.",
        _ADMIN,
    ),
    ROLE_FIELD_TECHNICIAN: BuiltinRole(
        "Assigned equipment and work orders, status updates, and report uploads.",
        _TECHNICIAN,
    ),
    ROLE_AUDITOR: BuiltinRole(
        "Read-only access to hospitals, equipment, work orders, users, and analytics.",
        _AUDITOR,
    ),
}


def has_permission(user: object, permission: Permission) -> bool:
    granted = getattr(user, "granted_permissions", ())
    return permission.value in granted


def missing_permission_detail(*permissions: Permission) -> str:
    names = ", ".join(permission.value for permission in permissions)
    return f"Missing permission: {names}"
