import { Layout, Typography } from "antd";
import { useTranslation } from "react-i18next";
import { Outlet } from "react-router-dom";

import { SideNav } from "@/app/layout/SideNav";
import { LanguageSwitcher } from "@/app/layout/LanguageSwitcher";

const { Header, Sider, Content } = Layout;

export function AppShell() {
  const { t } = useTranslation();

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
          <LanguageSwitcher />
        </Header>
        <Content style={{ padding: 24 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
