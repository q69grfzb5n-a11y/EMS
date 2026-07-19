import type { Permission } from "@/shared/auth/permissions";

export interface NavItem {
  key: string;
  labelKey: string;
  path: string;
  permission?: Permission;
}

export const NAV_ITEMS: NavItem[] = [
  { key: "dashboard", labelKey: "nav.dashboard", path: "/" },
  { key: "employees", labelKey: "nav.employees", path: "/employees" },
  { key: "org", labelKey: "nav.org", path: "/org", permission: "MANAGE_ORG" },
  { key: "users", labelKey: "nav.users", path: "/users", permission: "MANAGE_ROLES" },
];
