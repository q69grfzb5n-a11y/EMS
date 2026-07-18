import { Result } from "antd";
import { Outlet } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { useAuthStore } from "@/shared/auth/authStore";
import { hasPermission, type Permission } from "@/shared/auth/permissions";

interface RequirePermissionProps {
  permission: Permission;
}

export function RequirePermission({ permission }: RequirePermissionProps) {
  const { t } = useTranslation();
  const roles = useAuthStore((state) => state.user?.roles ?? []);

  if (!hasPermission(roles, permission)) {
    return <Result status="403" title="403" subTitle={t("common.notPermitted")} />;
  }

  return <Outlet />;
}
