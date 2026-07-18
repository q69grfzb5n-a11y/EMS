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
