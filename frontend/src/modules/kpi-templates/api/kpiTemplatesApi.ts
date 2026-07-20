import { apiClient } from "@/shared/api/client";
import type {
  KpiCriterionCreateRequest,
  KpiCriterionOut,
  KpiCriterionPatchRequest,
  KpiTemplateAssignmentCreateRequest,
  KpiTemplateAssignmentOut,
  KpiTemplateCreateRequest,
  KpiTemplateOut,
  KpiTemplateVersionOut,
} from "@/modules/kpi-templates/types";

export async function listTemplates(): Promise<KpiTemplateOut[]> {
  const { data } = await apiClient.get<KpiTemplateOut[]>("/kpi-templates");
  return data;
}

export async function getTemplate(id: number): Promise<KpiTemplateOut> {
  const { data } = await apiClient.get<KpiTemplateOut>(`/kpi-templates/${id}`);
  return data;
}

export async function createTemplate(payload: KpiTemplateCreateRequest): Promise<KpiTemplateOut> {
  const { data } = await apiClient.post<KpiTemplateOut>("/kpi-templates", payload);
  return data;
}

export async function listVersions(templateId: number): Promise<KpiTemplateVersionOut[]> {
  const { data } = await apiClient.get<KpiTemplateVersionOut[]>(
    `/kpi-templates/${templateId}/versions`,
  );
  return data;
}

export async function cloneVersion(
  templateId: number,
  sourceVersionId?: number,
): Promise<KpiTemplateVersionOut> {
  const { data } = await apiClient.post<KpiTemplateVersionOut>(
    `/kpi-templates/${templateId}/versions`,
    { source_version_id: sourceVersionId ?? null },
  );
  return data;
}

export async function getVersion(versionId: number): Promise<KpiTemplateVersionOut> {
  const { data } = await apiClient.get<KpiTemplateVersionOut>(
    `/kpi-templates/versions/${versionId}`,
  );
  return data;
}

export async function activateVersion(versionId: number): Promise<KpiTemplateVersionOut> {
  const { data } = await apiClient.post<KpiTemplateVersionOut>(
    `/kpi-templates/versions/${versionId}/activate`,
  );
  return data;
}

export async function createCriterion(
  versionId: number,
  payload: KpiCriterionCreateRequest,
): Promise<KpiCriterionOut> {
  const { data } = await apiClient.post<KpiCriterionOut>(
    `/kpi-templates/versions/${versionId}/criteria`,
    payload,
  );
  return data;
}

export async function patchCriterion(
  criterionId: number,
  payload: KpiCriterionPatchRequest,
): Promise<KpiCriterionOut> {
  const { data } = await apiClient.patch<KpiCriterionOut>(
    `/kpi-templates/criteria/${criterionId}`,
    payload,
  );
  return data;
}

export async function deleteCriterion(criterionId: number): Promise<void> {
  await apiClient.delete(`/kpi-templates/criteria/${criterionId}`);
}

export async function listPositionAssignments(
  positionId: number,
): Promise<KpiTemplateAssignmentOut[]> {
  const { data } = await apiClient.get<KpiTemplateAssignmentOut[]>(
    `/positions/${positionId}/kpi-template-assignments`,
  );
  return data;
}

export async function createPositionAssignment(
  positionId: number,
  payload: KpiTemplateAssignmentCreateRequest,
): Promise<KpiTemplateAssignmentOut> {
  const { data } = await apiClient.post<KpiTemplateAssignmentOut>(
    `/positions/${positionId}/kpi-template-assignments`,
    payload,
  );
  return data;
}
