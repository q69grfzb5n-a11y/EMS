import { useMemo, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Col,
  Collapse,
  Descriptions,
  Form,
  Input,
  InputNumber,
  Modal,
  Row,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";

import { ApprovalActionModal } from "@/modules/approvals/components/ApprovalActionModal";
import { ApprovalTimeline } from "@/modules/approvals/components/ApprovalTimeline";
import {
  approveRun,
  completeAudit,
  getRun,
  getRunHistory,
  recalculateRun,
  rejectRun,
  submitAudit,
  updateLine,
} from "@/modules/incentives/api/incentivesApi";
import { IncentiveLineBreakdown } from "@/modules/incentives/components/IncentiveLineBreakdown";
import { IncentiveRunStatusTag } from "@/modules/incentives/components/IncentiveRunStatusTag";
import type { ExceptionOut, IncentiveLineItemOut } from "@/modules/incentives/types";
import { ROLES, hasAnyRole } from "@/shared/auth/permissions";
import { useAuthStore } from "@/shared/auth/authStore";
import { useLocalizedField } from "@/shared/hooks/useLocalizedField";
import { Ltr } from "@/shared/ui/Ltr";

type Action = "submit_audit" | "complete_audit" | "approve" | "reject";

function availableActions(status: string, roles: string[]): Action[] {
  const actions: Action[] = [];
  if (status === "draft" && hasAnyRole(roles, [ROLES.HR, ROLES.PMO, ROLES.ADMIN])) {
    actions.push("submit_audit");
  }
  if (status === "pmo_audit" && roles.includes(ROLES.PMO)) {
    actions.push("complete_audit", "reject");
  }
  if (status === "fm_approval" && roles.includes(ROLES.FACTORY_MANAGER)) {
    actions.push("approve", "reject");
  }
  return actions;
}

interface DeptTotal {
  code: string;
  name: string;
  count: number;
  total: number;
}

export function IncentiveRunDetailPage() {
  const { id } = useParams<{ id: string }>();
  const runId = Number(id);
  const { t } = useTranslation(["common", "incentives", "approvals"]);
  const localized = useLocalizedField();
  const queryClient = useQueryClient();
  const currentUser = useAuthStore((s) => s.user);
  const [pendingAction, setPendingAction] = useState<Action | null>(null);
  const [editingLine, setEditingLine] = useState<IncentiveLineItemOut | null>(null);

  const runQuery = useQuery({
    queryKey: ["incentive-runs", runId],
    queryFn: () => getRun(runId),
    enabled: Number.isFinite(runId),
  });
  const historyQuery = useQuery({
    queryKey: ["incentive-runs", runId, "history"],
    queryFn: () => getRunHistory(runId),
    enabled: Number.isFinite(runId),
  });

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["incentive-runs", runId] });
    void queryClient.invalidateQueries({ queryKey: ["incentive-runs", runId, "history"] });
    void queryClient.invalidateQueries({ queryKey: ["incentive-runs"] });
  };

  const transitionMutation = useMutation({
    mutationFn: ({ action, comment }: { action: Action; comment?: string }) => {
      const fns = {
        submit_audit: submitAudit,
        complete_audit: completeAudit,
        approve: approveRun,
        reject: rejectRun,
      };
      return fns[action](runId, comment);
    },
    onSuccess: () => {
      void message.success(t("evaluations:transitionSuccess", { ns: "evaluations" }));
      setPendingAction(null);
      invalidate();
    },
    onError: () => void message.error(t("evaluations:transitionFailed", { ns: "evaluations" })),
  });

  const recalculateMutation = useMutation({
    mutationFn: () => recalculateRun(runId),
    onSuccess: () => {
      void message.success(t("incentives:recalculated"));
      invalidate();
    },
  });

  const deptTotals: DeptTotal[] = useMemo(() => {
    if (!runQuery.data) return [];
    const byDept = new Map<string, DeptTotal>();
    for (const line of runQuery.data.lines) {
      if (line.is_excluded) continue;
      const dept = line.employee.department;
      const existing = byDept.get(dept.code);
      const amount = Number(line.final_amount);
      if (existing) {
        existing.count += 1;
        existing.total += amount;
      } else {
        byDept.set(dept.code, {
          code: dept.code,
          name: localized(dept.name_en, dept.name_ar),
          count: 1,
          total: amount,
        });
      }
    }
    return Array.from(byDept.values()).sort((a, b) => b.total - a.total);
  }, [runQuery.data, localized]);

  if (!runQuery.data) return null;
  const run = runQuery.data;
  const roles = currentUser?.roles ?? [];
  const actions = availableActions(run.status, roles);
  const editable = run.status === "draft";
  const canEditLines = editable && hasAnyRole(roles, [ROLES.HR, ROLES.PMO, ROLES.ADMIN]);

  return (
    <div>
      <Space style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <Typography.Title level={3} style={{ margin: 0 }}>
          {t("incentives:runTitle", { runNo: run.run_no })}
        </Typography.Title>
        <Space>
          <IncentiveRunStatusTag status={run.status} />
          {run.status === "approved" && (
            <Tag color="purple">{t("incentives:periodLocked")}</Tag>
          )}
        </Space>
      </Space>

      <Row gutter={16}>
        <Col span={16}>
          <Card style={{ marginBottom: 16 }}>
            <Descriptions size="small" column={3}>
              <Descriptions.Item label={t("incentives:formulaMode")}>
                {t(`incentives:formulaModeValues.${run.params.formula_mode}`)}
              </Descriptions.Item>
              <Descriptions.Item label={t("incentives:lineCount")}>
                {run.lines.length}
              </Descriptions.Item>
              <Descriptions.Item label={t("incentives:totalFinalAmount")}>
                <Ltr>{run.total_final_amount}</Ltr>
              </Descriptions.Item>
            </Descriptions>

            {canEditLines && (
              <Button
                style={{ marginTop: 12 }}
                loading={recalculateMutation.isPending}
                onClick={() => recalculateMutation.mutate()}
              >
                {t("incentives:recalculate")}
              </Button>
            )}

            {actions.length > 0 && (
              <Space style={{ marginTop: 12, display: "block" }}>
                {actions.map((action) => (
                  <Button
                    key={action}
                    type={action === "reject" ? "default" : "primary"}
                    danger={action === "reject"}
                    onClick={() => setPendingAction(action)}
                  >
                    {t(`approvals:actions.${action}`)}
                  </Button>
                ))}
              </Space>
            )}
          </Card>

          <Card title={t("incentives:deptTotals")} style={{ marginBottom: 16 }}>
            <Table<DeptTotal>
              rowKey="code"
              size="small"
              pagination={false}
              dataSource={deptTotals}
              columns={[
                { title: t("incentives:department"), dataIndex: "name" },
                { title: t("incentives:lineCount"), dataIndex: "count", width: 100 },
                {
                  title: t("incentives:totalFinalAmount"),
                  key: "total",
                  render: (_: unknown, r: DeptTotal) => <Ltr>{r.total.toFixed(2)}</Ltr>,
                },
              ]}
            />
          </Card>

          {run.exceptions.length > 0 && (
            <Collapse
              style={{ marginBottom: 16 }}
              items={[
                {
                  key: "exceptions",
                  label: t("incentives:exceptionsCount", { count: run.exceptions.length }),
                  children: (
                    <Table<ExceptionOut>
                      size="small"
                      rowKey={(r) => r.employee_id}
                      pagination={{ pageSize: 20 }}
                      dataSource={run.exceptions}
                      columns={[
                        {
                          title: t("evaluations:staffNo", { ns: "evaluations" }),
                          dataIndex: "staff_no",
                          render: (v: string) => <Ltr>{v}</Ltr>,
                        },
                        {
                          title: t("incentives:reason"),
                          key: "reason",
                          render: (_: unknown, r: ExceptionOut) =>
                            t(`incentives:exceptionReasons.${r.reason}`, {
                              defaultValue: r.reason,
                            }),
                        },
                      ]}
                    />
                  ),
                },
              ]}
            />
          )}

          <Table<IncentiveLineItemOut>
            rowKey="id"
            size="small"
            pagination={{ pageSize: 50 }}
            dataSource={run.lines}
            columns={[
              {
                title: t("evaluations:staffNo", { ns: "evaluations" }),
                key: "staff_no",
                render: (_: unknown, l: IncentiveLineItemOut) => <Ltr>{l.employee.staff_no}</Ltr>,
              },
              {
                title: t("evaluations:employeeName", { ns: "evaluations" }),
                key: "name",
                render: (_: unknown, l: IncentiveLineItemOut) => (
                  <bdi>{localized(l.employee.full_name_en, l.employee.full_name_ar)}</bdi>
                ),
              },
              {
                title: t("incentives:department"),
                key: "dept",
                render: (_: unknown, l: IncentiveLineItemOut) => (
                  <bdi>{localized(l.employee.department.name_en, l.employee.department.name_ar)}</bdi>
                ),
              },
              {
                title: t("incentives:finalAmount"),
                key: "final",
                render: (_: unknown, l: IncentiveLineItemOut) => <Ltr>{l.final_amount}</Ltr>,
              },
              {
                title: t("incentives:excluded"),
                key: "excluded",
                render: (_: unknown, l: IncentiveLineItemOut) =>
                  l.is_excluded ? <Tag color="red">{t("incentives:excluded")}</Tag> : null,
              },
              {
                title: t("common:common.edit"),
                key: "actions",
                render: (_: unknown, l: IncentiveLineItemOut) => (
                  <Button size="small" onClick={() => setEditingLine(l)}>
                    {t("incentives:viewLine")}
                  </Button>
                ),
              },
            ]}
          />
        </Col>
        <Col span={8}>
          <Card title={t("approvals:timeline.title")}>
            <ApprovalTimeline history={historyQuery.data ?? []} />
          </Card>
        </Col>
      </Row>

      {editingLine && (
        <LineEditModal
          runId={runId}
          line={editingLine}
          editable={canEditLines}
          onClose={() => setEditingLine(null)}
          onSaved={() => {
            setEditingLine(null);
            invalidate();
          }}
        />
      )}

      {pendingAction && (
        <ApprovalActionModal
          action={pendingAction}
          open
          loading={transitionMutation.isPending}
          requireComment={pendingAction === "reject"}
          onCancel={() => setPendingAction(null)}
          onConfirm={(comment) => transitionMutation.mutate({ action: pendingAction, comment })}
        />
      )}
    </div>
  );
}

function LineEditModal({
  runId,
  line,
  editable,
  onClose,
  onSaved,
}: {
  runId: number;
  line: IncentiveLineItemOut;
  editable: boolean;
  onClose: () => void;
  onSaved: () => void;
}) {
  const { t } = useTranslation(["common", "incentives"]);
  const [attendanceFactor, setAttendanceFactor] = useState(Number(line.attendance_factor));
  const [overrideAmount, setOverrideAmount] = useState<number | null>(
    line.override_amount ? Number(line.override_amount) : null,
  );
  const [overrideReason, setOverrideReason] = useState(line.override_reason ?? "");
  const [isExcluded, setIsExcluded] = useState(line.is_excluded);
  const [excludeReason, setExcludeReason] = useState(line.exclude_reason ?? "");

  const mutation = useMutation({
    mutationFn: () =>
      updateLine(runId, line.id, {
        row_version: line.row_version,
        attendance_factor: String(attendanceFactor),
        override_amount: overrideAmount !== null ? String(overrideAmount) : null,
        override_reason: overrideAmount !== null ? overrideReason : null,
        clear_override: overrideAmount === null,
        is_excluded: isExcluded,
        exclude_reason: isExcluded ? excludeReason : null,
      }),
    onSuccess: () => {
      void message.success(t("incentives:lineSaved"));
      onSaved();
    },
    onError: () => void message.error(t("incentives:lineSaveFailed")),
  });

  return (
    <Modal
      title={<bdi>{line.employee.full_name_en ?? line.employee.full_name_ar}</bdi>}
      open
      onCancel={onClose}
      footer={null}
      width={600}
      destroyOnHidden
    >
      <IncentiveLineBreakdown line={line} />

      {editable && (
        <Form layout="vertical" style={{ marginTop: 16 }} onFinish={() => mutation.mutate()}>
          <Form.Item label={t("incentives:breakdown.attendanceFactor")}>
            <InputNumber
              style={{ width: "100%" }}
              min={0}
              max={1.2}
              step={0.01}
              value={attendanceFactor}
              onChange={(v) => setAttendanceFactor(v ?? 1)}
            />
          </Form.Item>
          <Form.Item label={t("incentives:overrideAmount")}>
            <InputNumber
              style={{ width: "100%" }}
              min={0}
              value={overrideAmount ?? undefined}
              onChange={(v) => setOverrideAmount(v ?? null)}
            />
          </Form.Item>
          {overrideAmount !== null && (
            <Form.Item label={t("incentives:overrideReason")} required>
              <Input value={overrideReason} onChange={(e) => setOverrideReason(e.target.value)} />
            </Form.Item>
          )}
          <Form.Item label={t("incentives:excluded")}>
            <Switch checked={isExcluded} onChange={setIsExcluded} />
          </Form.Item>
          {isExcluded && (
            <Form.Item label={t("incentives:excludeReason")} required>
              <Input value={excludeReason} onChange={(e) => setExcludeReason(e.target.value)} />
            </Form.Item>
          )}
          {(overrideAmount !== null && !overrideReason) || (isExcluded && !excludeReason) ? (
            <Alert
              type="warning"
              showIcon
              style={{ marginBottom: 12 }}
              message={t("incentives:reasonRequiredHint")}
            />
          ) : null}
          <Button
            type="primary"
            htmlType="submit"
            block
            loading={mutation.isPending}
            disabled={(overrideAmount !== null && !overrideReason) || (isExcluded && !excludeReason)}
          >
            {t("common:common.save")}
          </Button>
        </Form>
      )}
    </Modal>
  );
}

export default IncentiveRunDetailPage;
