import { Menu } from "antd";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate } from "react-router-dom";

import { NAV_ITEMS } from "@/app/layout/navigation";
import { useAuthStore } from "@/shared/auth/authStore";
import { hasPermission } from "@/shared/auth/permissions";

export function SideNav() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const roles = useAuthStore((state) => state.user?.roles ?? []);

  const visibleItems = NAV_ITEMS.filter(
    (item) => !item.permission || hasPermission(roles, item.permission),
  );

  return (
    <Menu
      mode="inline"
      selectedKeys={[location.pathname]}
      items={visibleItems.map((item) => ({
        key: item.path,
        label: t(item.labelKey),
      }))}
      onClick={({ key }) => navigate(key)}
    />
  );
}
