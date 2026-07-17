import { Menu } from "antd";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate } from "react-router-dom";

import { NAV_ITEMS } from "@/app/layout/navigation";

export function SideNav() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <Menu
      mode="inline"
      selectedKeys={[location.pathname]}
      items={NAV_ITEMS.map((item) => ({
        key: item.path,
        label: t(item.labelKey),
      }))}
      onClick={({ key }) => navigate(key)}
    />
  );
}
