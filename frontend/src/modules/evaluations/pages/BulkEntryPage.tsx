import { useState } from "react";
import { Alert, Button, Form, Modal, Popconfirm, Select, Space, Typography, message } from "antd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { isAxiosError } from "axios";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { listPeriods } from "@/modules/attendance/api/attendanceApi";
import {
  bulkCreateEvaluations,
  createSelfAppraisal,
  listEvaluations,
  submitEvaluation,
} from "@/modules/evaluations/api/evaluationsApi";
import { EvaluationScoresForm, EvaluationStatusTag } from "@/modules/evaluations/components/EvaluationScoresForm";
import type { EvaluationOut } from "@/modules/evaluations/types";
import { listDepartments } from "@/modules/org/api/orgApi";
import { Can } from "@/shared/auth/Can";
import { useAuthStore } from "@/shared/auth/authStore";
import { ROLES, hasAnyRole } from "@/shared/auth/permissions";
import { useLocalizedField } from "@/shared/hooks/useLocalizedField";
import { DataTable } from "@/shared/ui/DataTable";
import { Ltr } from "@/shared/ui/Ltr";

export function BulkEntryPage() {
  const { t } = useTranslation(["common", "evaluations"]);
  const navigate = useNavigate();
  const localized = useLocalizedField();
  const queryClient = useQueryClient();
  const currentUser = useAuthStore((s) => s.user);
  const [periodId, setPeriodId] = useState<number | null>(null);
  const [editing, setEditing] = useState<EvaluationOut | null>(null);
  const [bulkCreateOpen, setBulkCreateOpen] = useState(false);

  const periodsQuery = useQuery({ queryKey: ["attendance", "periods"], queryFn: listPeriods });
  const departmentsQuery = useQuery({ queryKey: ["org", "departments"], queryFn: listDepartments });
  const evaluationsQuery = useQuery({
    queryKey: ["evaluations", "byPeriod", periodId],
    queryFn: () => listEvaluations(periodId ?? undefined),
    enabled: periodId !== null,
  });

  const submitMutation = useMutation({
    mutationFn: (evaluationId: number) => submitEvaluation(evaluationId),
    onSuccess: () => {
      void message.success(t("evaluations:transitionSuccess"));
      void queryClient.invalidateQueries({ queryKey: ["evaluations"] });
    },
    onError: () => void message.error(t("evaluations:transitionFailed")),
  });

  const bulkCreateMutation = useMutation({
    mutationFn: (payload: { department_id: number }) =>
      bulkCreateEvaluations({ department_id: payload.department_id, period_id: periodId as number }),
    onSuccess: (result) => {
      void message.success(
        t("evaluations:bulkCreateResult", { created: result.created.length, skipped: result.skipped.length }),
      );
      setBulkCreateOpen(false);
      void queryClient.invalidateQueries({ queryKey: ["evaluations"] });
    },
  });

  const selfAppraisalMutation = useMutation({
    mutationFn: () => createSelfAppraisal({ period_id: periodId as number }),
    onSuccess: (evaluation) => {
      void message.success(t("evaluations:selfAppraisal.created"));
      void queryClient.invalidateQueries({ queryKey: ["evaluations"] });
      navigate(`/evaluations/${evaluation.id}`);
    },
    onError: (err: unknown) => {
      const code =
        isAxiosError(err) && typeof err.response?.data?.error?.code === "string"
          ? (err.response.data.error.code as string)
          : "unknown_error";
      void message.error(
        t(`evaluations:selfAppraisal.errors.${code}`, {
          defaultValue: t("evaluations:selfAppraisal.errors.unknown_error"),
        }),
      );
    },
  });

  const isKeyPerson = hasAnyRole(currentUser?.roles ?? [], [ROLES.KEY_PERSON]);

  return (
    <div>
      <Space style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <Typography.Title level={3} style={{ margin: 0 }}>
          {t("evaluations:bulkEntry.title")}
        </Typography.Title>
        <Space>
          {isKeyPerson && (
            <Button
              disabled={!periodId}
              loading={selfAppraisalMutation.isPending}
              onClick={() => selfAppraisalMutation.mutate()}
            >
              {t("evaluations:selfAppraisal.start")}
            </Button>
          )}
          <Can permission="CREATE_EVALUATIONS">
            <Button type="primary" disabled={!periodId} onClick={() => setBulkCreateOpen(true)}>
              {t("evaluations:bulkEntry.createForDepartment")}
            </Button>
          </Can>
        </Space>
      </Space>

      <Select
        style={{ minWidth: 220, marginBottom: 16 }}
        placeholder={t("attendance:period", { ns: "attendance" })}
        value={periodId ?? undefined}
        onChange={setPeriodId}
        options={(periodsQuery.data ?? []).map((p) => ({
          value: p.id,
          label: `${String(p.month).padStart(2, "0")}-${p.year}`,
        }))}
      />

      {evaluationsQuery.isError && (
        <Alert
          type="error"
          showIcon
          message={t("common:common.loadError")}
          style={{ marginBottom: 16 }}
          action={
            <Button size="small" onClick={() => void evaluationsQuery.refetch()}>
              {t("common:common.retry")}
            </Button>
          }
        />
      )}

      <DataTable<EvaluationOut>
        rowKey="id"
        loading={evaluationsQuery.isLoading}
        dataSource={evaluationsQuery.data ?? []}
        searchableText={(e) => [e.employee.staff_no, e.employee.full_name_en ?? "", e.employee.full_name_ar]}
        columns={[
          {
            title: t("evaluations:staffNo"),
            key: "staff_no",
            render: (_: unknown, e: EvaluationOut) => <Ltr>{e.employee.staff_no}</Ltr>,
          },
          {
            title: t("evaluations:employeeName"),
            key: "name",
            render: (_: unknown, e: EvaluationOut) => (
              <bdi>{localized(e.employee.full_name_en, e.employee.full_name_ar)}</bdi>
            ),
          },
          {
            title: t("common:common.active"),
            key: "status",
            render: (_: unknown, e: EvaluationOut) => <EvaluationStatusTag status={e.status} />,
          },
          {
            title: t("evaluations:scorePct"),
            key: "score",
            render: (_: unknown, e: EvaluationOut) =>
              e.score_pct ? <Ltr>{(Number(e.score_pct) * 100).toFixed(1)}%</Ltr> : "—",
          },
          {
            title: t("common:common.edit"),
            key: "actions",
            render: (_: unknown, e: EvaluationOut) => {
              const isOwner = currentUser !== null && e.owner_user_id === currentUser.id;
              const canEdit = isOwner && (e.status === "draft" || e.status === "returned");
              return (
                <Space>
                  <Button size="small" onClick={() => navigate(`/evaluations/${e.id}`)}>
                    {t("evaluations:bulkEntry.open")}
                  </Button>
                  {canEdit && (
                    <>
                      <Button size="small" onClick={() => setEditing(e)}>
                        {t("common:common.edit")}
                      </Button>
                      <Popconfirm
                        title={t("evaluations:bulkEntry.submitConfirmTitle")}
                        description={t("evaluations:bulkEntry.submitConfirmDescription")}
                        onConfirm={() => submitMutation.mutate(e.id)}
                        okText={t("approvals:actions.submit", { ns: "approvals" })}
                        cancelText={t("common:common.cancel")}
                      >
                        <Button
                          size="small"
                          type="primary"
                          loading={submitMutation.isPending && submitMutation.variables === e.id}
                        >
                          {t("approvals:actions.submit", { ns: "approvals" })}
                        </Button>
                      </Popconfirm>
                    </>
                  )}
                </Space>
              );
            },
          },
        ]}
      />

      {editing && (
        <Modal
          title={<bdi>{localized(editing.employee.full_name_en, editing.employee.full_name_ar)}</bdi>}
          open
          onCancel={() => setEditing(null)}
          footer={null}
          width={800}
          destroyOnHidden
        >
          <EvaluationScoresForm
            evaluation={editing}
            editable
            onSaved={() => {
              setEditing(null);
              void queryClient.invalidateQueries({ queryKey: ["evaluations"] });
            }}
          />
        </Modal>
      )}

      <Modal
        title={t("evaluations:bulkEntry.createForDepartment")}
        open={bulkCreateOpen}
        onCancel={() => setBulkCreateOpen(false)}
        footer={null}
        destroyOnHidden
      >
        <Form
          layout="vertical"
          onFinish={(values: { department_id: number }) => bulkCreateMutation.mutate(values)}
        >
          <Form.Item name="department_id" label={t("evaluations:bulkEntry.department")} rules={[{ required: true }]}>
            <Select
              options={(departmentsQuery.data ?? []).map((d) => ({
                value: d.id,
                label: `${d.code} — ${localized(d.name_en, d.name_ar)}`,
              }))}
            />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={bulkCreateMutation.isPending} block>
              {t("common:common.create")}
            </Button>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

export default BulkEntryPage;
