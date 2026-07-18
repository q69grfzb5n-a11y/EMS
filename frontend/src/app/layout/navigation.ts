import type { Permission } from "@/shared/auth/permissions";

export interface NavItem {
  key: string;
  labelKey: string;
  path: string;
  permission?: Permission;
}

export const NAV_ITEMS: NavItem[] = [
  { key: "dashboard", labelKey: "nav.dashboard", path: "/" },
  { key: "users", labelKey: "nav.users", path: "/users", permission: "MANAGE_ROLES" },
];
