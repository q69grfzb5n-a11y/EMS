import type { PropsWithChildren } from "react";

import { useAuthStore } from "@/shared/auth/authStore";
import { hasPermission, type Permission } from "@/shared/auth/permissions";

interface CanProps extends PropsWithChildren {
  permission: Permission;
}

export function Can({ permission, children }: CanProps) {
  const roles = useAuthStore((state) => state.user?.roles ?? []);
  if (!hasPermission(roles, permission)) {
    return null;
  }
  return children;
}
