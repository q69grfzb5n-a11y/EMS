import { apiClient } from "@/shared/api/client";
import type { AuditLogFilters, AuditLogListOut } from "@/modules/audit/types";

export async function listAuditLog(filters: AuditLogFilters): Promise<AuditLogListOut> {
  const { data } = await apiClient.get<AuditLogListOut>("/audit-log", { params: filters });
  return data;
}
