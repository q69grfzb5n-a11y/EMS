export const ROLES = {
  HR: "hr",
  ADMIN: "admin",
  PMO: "pmo",
  FACTORY_MANAGER: "factory_manager",
  DEPT_MANAGER: "dept_manager",
  REVIEWER: "reviewer",
  FINANCE: "finance",
  KEY_PERSON: "key_person",
  EMPLOYEE: "employee",
} as const;

export type RoleCode = (typeof ROLES)[keyof typeof ROLES];

export const PERMISSIONS = {
  MANAGE_USERS: [ROLES.ADMIN, ROLES.HR],
  MANAGE_ROLES: [ROLES.HR],
  MANAGE_ORG: [ROLES.HR],
  MANAGE_EMPLOYEES: [ROLES.HR],
  VIEW_SALARY: [ROLES.HR, ROLES.FINANCE, ROLES.PMO],
} as const satisfies Record<string, readonly RoleCode[]>;

export type Permission = keyof typeof PERMISSIONS;

export function hasPermission(userRoles: readonly string[], permission: Permission): boolean {
  return PERMISSIONS[permission].some((role) => userRoles.includes(role));
}

export function hasAnyRole(userRoles: readonly string[], roles: readonly RoleCode[]): boolean {
  return roles.some((role) => userRoles.includes(role));
}
