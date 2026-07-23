import { startTransition } from "react";
import { LogoutOutlined } from "@ant-design/icons";
import { Button, Grid, Layout, Space, Typography } from "antd";
import { useTranslation } from "react-i18next";
import { Outlet, useNavigate } from "react-router-dom";

import { BrandMark } from "@/app/layout/BrandMark";
import { SideNav } from "@/app/layout/SideNav";
import { LanguageSwitcher } from "@/app/layout/LanguageSwitcher";
import { logout as logoutRequest } from "@/modules/auth/api/authApi";
import { Ltr } from "@/shared/ui/Ltr";
import { useAuthStore } from "@/shared/auth/authStore";

const { Header, Sider, Content } = Layout;
const { useBreakpoint } = Grid;

export function AppShell() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const clearAuth = useAuthStore((state) => state.clear);
  const staffNo = useAuthStore((state) => state.user?.staff_no);
  const screens = useBreakpoint();

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
      <Sider breakpoint="lg" collapsedWidth="0" style={{ borderInlineEnd: "1px solid #f0f0f0" }}>
        <SideNav />
      </Sider>
      <Layout>
        <Header
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 16,
            paddingInline: 16,
          }}
        >
          <Space size={10} style={{ minWidth: 0 }}>
            <BrandMark size={30} />
            <Space direction="vertical" size={0} style={{ lineHeight: 1.2, minWidth: 0 }}>
              <Typography.Text strong style={{ color: "#fff", fontSize: 15 }}>
                {t("app.orgShort")}
              </Typography.Text>
              {screens.sm && (
                <Typography.Text
                  style={{ color: "rgba(255,255,255,0.75)", fontSize: 12 }}
                  ellipsis
                >
                  {t("app.name")}
                </Typography.Text>
              )}
            </Space>
          </Space>
          <Space size={screens.sm ? 12 : 4}>
            {staffNo && screens.sm && (
              <Typography.Text style={{ color: "rgba(255,255,255,0.85)" }}>
                <Ltr>{staffNo}</Ltr>
              </Typography.Text>
            )}
            <LanguageSwitcher />
            <Button
              type="text"
              icon={<LogoutOutlined />}
              style={{ color: "#fff" }}
              onClick={() => void handleLogout()}
            >
              {screens.sm ? t("auth.logout") : null}
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
