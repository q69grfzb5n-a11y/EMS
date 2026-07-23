import {
  ApartmentOutlined,
  AuditOutlined,
  BankOutlined,
  CalendarOutlined,
  CheckSquareOutlined,
  DashboardOutlined,
  DollarCircleOutlined,
  FileTextOutlined,
  SwapOutlined,
  TeamOutlined,
  UserOutlined,
  UsergroupAddOutlined,
  WalletOutlined,
} from "@ant-design/icons";
import type { ComponentType } from "react";

import type { Permission } from "@/shared/auth/permissions";

export interface NavItem {
  key: string;
  labelKey: string;
  path: string;
  icon: ComponentType;
  permission?: Permission;
}

export const NAV_ITEMS: NavItem[] = [
  { key: "dashboard", labelKey: "nav.dashboard", path: "/", icon: DashboardOutlined },
  { key: "employees", labelKey: "nav.employees", path: "/employees", icon: TeamOutlined },
  {
    key: "org",
    labelKey: "nav.org",
    path: "/org",
    icon: ApartmentOutlined,
    permission: "MANAGE_ORG",
  },
  {
    key: "kpiTemplates",
    labelKey: "nav.kpiTemplates",
    path: "/kpi-templates",
    icon: FileTextOutlined,
    permission: "MANAGE_KPI_TEMPLATES",
  },
  {
    key: "attendance",
    labelKey: "nav.attendance",
    path: "/attendance",
    icon: CalendarOutlined,
    permission: "MANAGE_PERIODS",
  },
  { key: "myTeam", labelKey: "nav.myTeam", path: "/evaluations", icon: UsergroupAddOutlined },
  { key: "transfers", labelKey: "nav.transfers", path: "/transfers", icon: SwapOutlined },
  { key: "approvals", labelKey: "nav.approvals", path: "/approvals", icon: CheckSquareOutlined },
  {
    key: "incentives",
    labelKey: "nav.incentives",
    path: "/incentives",
    icon: DollarCircleOutlined,
  },
  {
    key: "myIncentives",
    labelKey: "nav.myIncentives",
    path: "/my-incentives",
    icon: WalletOutlined,
  },
  {
    key: "reports",
    labelKey: "nav.finance",
    path: "/reports",
    icon: BankOutlined,
    permission: "VIEW_FINANCE_REPORTS",
  },
  {
    key: "audit",
    labelKey: "nav.audit",
    path: "/audit-log",
    icon: AuditOutlined,
    permission: "VIEW_AUDIT_LOG",
  },
  {
    key: "users",
    labelKey: "nav.users",
    path: "/users",
    icon: UserOutlined,
    permission: "MANAGE_ROLES",
  },
];
