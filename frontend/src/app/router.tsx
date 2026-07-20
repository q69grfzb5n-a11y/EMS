import { createBrowserRouter } from "react-router-dom";

import { AppShell } from "@/app/layout/AppShell";
import { RequireAuth } from "@/app/guards/RequireAuth";
import { RequirePermission } from "@/app/guards/RequirePermission";

export const router = createBrowserRouter([
  {
    path: "/login",
    lazy: async () => {
      const { LoginPage } = await import("@/modules/auth/pages/LoginPage");
      return { Component: LoginPage };
    },
  },
  {
    element: <RequireAuth />,
    children: [
      {
        path: "/change-password",
        lazy: async () => {
          const { ChangePasswordPage } = await import(
            "@/modules/auth/pages/ChangePasswordPage"
          );
          return { Component: ChangePasswordPage };
        },
      },
      {
        path: "/",
        element: <AppShell />,
        children: [
          {
            index: true,
            lazy: async () => {
              const { DashboardPage } = await import("@/modules/dashboard/pages/DashboardPage");
              return { Component: DashboardPage };
            },
          },
          {
            path: "employees",
            lazy: async () => {
              const { EmployeesListPage } = await import(
                "@/modules/employees/pages/EmployeesListPage"
              );
              return { Component: EmployeesListPage };
            },
          },
          {
            path: "employees/:id",
            lazy: async () => {
              const { EmployeeDetailPage } = await import(
                "@/modules/employees/pages/EmployeeDetailPage"
              );
              return { Component: EmployeeDetailPage };
            },
          },
          {
            element: <RequirePermission permission="MANAGE_ORG" />,
            children: [
              {
                path: "org",
                lazy: async () => {
                  const { OrgPage } = await import("@/modules/org/pages/OrgPage");
                  return { Component: OrgPage };
                },
              },
            ],
          },
          {
            element: <RequirePermission permission="MANAGE_KPI_TEMPLATES" />,
            children: [
              {
                path: "kpi-templates",
                lazy: async () => {
                  const { KpiTemplatesListPage } = await import(
                    "@/modules/kpi-templates/pages/KpiTemplatesListPage"
                  );
                  return { Component: KpiTemplatesListPage };
                },
              },
              {
                path: "kpi-templates/:id",
                lazy: async () => {
                  const { KpiTemplateDetailPage } = await import(
                    "@/modules/kpi-templates/pages/KpiTemplateDetailPage"
                  );
                  return { Component: KpiTemplateDetailPage };
                },
              },
            ],
          },
          {
            element: <RequirePermission permission="MANAGE_PERIODS" />,
            children: [
              {
                path: "attendance",
                lazy: async () => {
                  const { AttendancePeriodsPage } = await import(
                    "@/modules/attendance/pages/AttendancePeriodsPage"
                  );
                  return { Component: AttendancePeriodsPage };
                },
              },
              {
                path: "attendance/zero-flags",
                lazy: async () => {
                  const { ZeroFlagsPage } = await import(
                    "@/modules/attendance/pages/ZeroFlagsPage"
                  );
                  return { Component: ZeroFlagsPage };
                },
              },
              {
                path: "attendance/:id",
                lazy: async () => {
                  const { AttendancePeriodDetailPage } = await import(
                    "@/modules/attendance/pages/AttendancePeriodDetailPage"
                  );
                  return { Component: AttendancePeriodDetailPage };
                },
              },
            ],
          },
          {
            path: "evaluations",
            lazy: async () => {
              const { BulkEntryPage } = await import("@/modules/evaluations/pages/BulkEntryPage");
              return { Component: BulkEntryPage };
            },
          },
          {
            path: "evaluations/:id",
            lazy: async () => {
              const { EvaluationDetailPage } = await import(
                "@/modules/evaluations/pages/EvaluationDetailPage"
              );
              return { Component: EvaluationDetailPage };
            },
          },
          {
            path: "approvals",
            lazy: async () => {
              const { ApprovalsInboxPage } = await import(
                "@/modules/approvals/pages/ApprovalsInboxPage"
              );
              return { Component: ApprovalsInboxPage };
            },
          },
          {
            element: <RequirePermission permission="MANAGE_ROLES" />,
            children: [
              {
                path: "users",
                lazy: async () => {
                  const { UsersAdminPage } = await import(
                    "@/modules/auth/pages/UsersAdminPage"
                  );
                  return { Component: UsersAdminPage };
                },
              },
            ],
          },
        ],
      },
    ],
  },
]);
