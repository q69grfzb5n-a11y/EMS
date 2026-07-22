import { apiClient } from "@/shared/api/client";
import type { PeriodSummaryOut } from "@/modules/reports/types";

export async function getPeriodSummary(periodId: number): Promise<PeriodSummaryOut> {
  const { data } = await apiClient.get<PeriodSummaryOut>(`/reports/periods/${periodId}/summary`);
  return data;
}

async function downloadBlob(url: string): Promise<Blob> {
  const { data } = await apiClient.get<Blob>(url, { responseType: "blob" });
  return data;
}

export const downloadFinanceExcel = (runId: number): Promise<Blob> =>
  downloadBlob(`/reports/runs/${runId}/finance-excel`);
export const downloadFinancePdf = (runId: number): Promise<Blob> =>
  downloadBlob(`/reports/runs/${runId}/finance-pdf`);
export const downloadBlankTemplateExcel = (versionId: number): Promise<Blob> =>
  downloadBlob(`/reports/kpi-templates/${versionId}/blank-excel`);
export const downloadBlankTemplatePdf = (versionId: number): Promise<Blob> =>
  downloadBlob(`/reports/kpi-templates/${versionId}/blank-pdf`);
