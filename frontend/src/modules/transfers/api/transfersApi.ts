import { apiClient } from "@/shared/api/client";
import type { TransferCreateRequest, TransferRequestOut } from "@/modules/transfers/types";
import type { ApprovalActionOut } from "@/shared/types/approvals";

export async function listTransfers(): Promise<TransferRequestOut[]> {
  const { data } = await apiClient.get<TransferRequestOut[]>("/transfers");
  return data;
}

export async function createTransfer(payload: TransferCreateRequest): Promise<TransferRequestOut> {
  const { data } = await apiClient.post<TransferRequestOut>("/transfers", payload);
  return data;
}

export async function getTransfer(id: number): Promise<TransferRequestOut> {
  const { data } = await apiClient.get<TransferRequestOut>(`/transfers/${id}`);
  return data;
}

async function transition(id: number, action: string, comment?: string): Promise<TransferRequestOut> {
  const { data } = await apiClient.post<TransferRequestOut>(`/transfers/${id}/${action}`, { comment });
  return data;
}

export const submitTransfer = (id: number, comment?: string) => transition(id, "submit", comment);
export const reviewTransfer = (id: number, comment?: string) => transition(id, "review", comment);
export const approveTransfer = (id: number, comment?: string) => transition(id, "approve", comment);
export const returnTransfer = (id: number, comment?: string) => transition(id, "return", comment);

export async function getTransferHistory(id: number): Promise<ApprovalActionOut[]> {
  const { data } = await apiClient.get<ApprovalActionOut[]>(`/approvals/transfer/${id}/history`);
  return data;
}
