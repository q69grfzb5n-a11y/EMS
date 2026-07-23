import { Menu } from "antd";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate } from "react-router-dom";

import { NAV_ITEMS } from "@/app/layout/navigation";
import { useAuthStore } from "@/shared/auth/authStore";
import { hasPermission } from "@/shared/auth/permissions";

/** `/employees/42` should still highlight the "Employees" nav item — matches
 * the item whose path is an exact or parent-segment match, preferring the
 * longest (most specific) match. The root "/" only ever matches itself,
 * otherwise every path would match it as a prefix. */
function findSelectedKey(pathname: string): string | undefined {
  const candidates = NAV_ITEMS.filter(
    (item) =>
      item.path !== "/" && (pathname === item.path || pathname.startsWith(`${item.path}/`)),
  );
  if (candidates.length > 0) {
    return candidates.reduce((longest, item) =>
      item.path.length > longest.path.length ? item : longest,
    ).path;
  }
  return pathname === "/" ? "/" : undefined;
}

export function SideNav() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const roles = useAuthStore((state) => state.user?.roles ?? []);

  const visibleItems = NAV_ITEMS.filter(
    (item) => !item.permission || hasPermission(roles, item.permission),
  );
  const selectedKey = findSelectedKey(location.pathname);

  return (
    <Menu
      mode="inline"
      selectedKeys={selectedKey ? [selectedKey] : []}
      items={visibleItems.map((item) => ({
        key: item.path,
        icon: <item.icon />,
        label: t(item.labelKey),
      }))}
      onClick={({ key }) => navigate(key)}
    />
  );
}
