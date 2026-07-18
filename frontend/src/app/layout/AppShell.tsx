import { startTransition } from "react";
import { Button, Layout, Space, Typography } from "antd";
import { useTranslation } from "react-i18next";
import { Outlet, useNavigate } from "react-router-dom";

import { SideNav } from "@/app/layout/SideNav";
import { LanguageSwitcher } from "@/app/layout/LanguageSwitcher";
import { logout as logoutRequest } from "@/modules/auth/api/authApi";
import { useAuthStore } from "@/shared/auth/authStore";

const { Header, Sider, Content } = Layout;

export function AppShell() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const clearAuth = useAuthStore((state) => state.clear);
  const staffNo = useAuthStore((state) => state.user?.staff_no);

  const handleLogout = async () => {
    try {
      await logoutRequest();
    } finally {
      clearAuth();
      startTransition(() => {
        navigate("/login", { replace: true });
      });
    }
  };

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider breakpoint="lg" collapsedWidth="0">
        <SideNav />
      </Sider>
      <Layout>
        <Header style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <Typography.Title level={4} style={{ margin: 0, color: "#fff" }}>
            {t("app.name")}
          </Typography.Title>
          <Space>
            {staffNo && <Typography.Text style={{ color: "#fff" }}>{staffNo}</Typography.Text>}
            <LanguageSwitcher />
            <Button type="text" style={{ color: "#fff" }} onClick={() => void handleLogout()}>
              {t("auth.logout")}
            </Button>
          </Space>
        </Header>
        <Content style={{ padding: 24 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
