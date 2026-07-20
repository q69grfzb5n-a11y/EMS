import { apiClient } from "@/shared/api/client";
import type { PendingItemOut } from "@/shared/types/approvals";

export async function listPendingApprovals(): Promise<PendingItemOut[]> {
  const { data } = await apiClient.get<PendingItemOut[]>("/approvals/pending");
  return data;
}
