import { createBrowserRouter } from "react-router-dom";

import { AppShell } from "@/app/layout/AppShell";

export const router = createBrowserRouter([
  {
    path: "/login",
    lazy: async () => {
      const { LoginPage } = await import("@/modules/auth/pages/LoginPage");
      return { Component: LoginPage };
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
    ],
  },
]);
