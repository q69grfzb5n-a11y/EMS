import { useState } from "react";
import { Alert, Button, Card, Col, Descriptions, Row, Space, Typography, message } from "antd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";

import {
  approveEvaluation,
  getEvaluation,
  getEvaluationHistory,
  returnEvaluation,
  reviewEvaluation,
  submitEvaluation,
} from "@/modules/evaluations/api/evaluationsApi";
import { EvaluationScoresForm, EvaluationStatusTag } from "@/modules/evaluations/components/EvaluationScoresForm";
import { ApprovalActionModal } from "@/modules/approvals/components/ApprovalActionModal";
import { ApprovalTimeline } from "@/modules/approvals/components/ApprovalTimeline";
import type { EvaluationOut } from "@/modules/evaluations/types";
import { useAuthStore } from "@/shared/auth/authStore";
import { useLocalizedField } from "@/shared/hooks/useLocalizedField";
import { Ltr } from "@/shared/ui/Ltr";
import { QueryState } from "@/shared/ui/QueryState";

type Action = "submit" | "approve" | "return" | "review";

function availableActions(status: string, kind: string, roles: string[], isOwner: boolean): Action[] {
  const actions: Action[] = [];
  if ((status === "draft" || status === "returned") && isOwner) {
    actions.push("submit");
  }
  if (kind === "regular") {
    if (status === "submitted" && roles.includes("dept_manager")) {
      actions.push("approve", "return");
    }
  } else {
    if (status === "submitted" && roles.includes("pmo")) {
      actions.push("review", "return");
    }
    if (status === "pmo_reviewed" && roles.includes("factory_manager")) {
      actions.push("approve", "return");
    }
  }
  return actions;
}

export function EvaluationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const evaluationId = Number(id);

  const evaluationQuery = useQuery({
    queryKey: ["evaluations", evaluationId],
    queryFn: () => getEvaluation(evaluationId),
    enabled: Number.isFinite(evaluationId),
  });

  return (
    <QueryState
      isLoading={evaluationQuery.isLoading}
      isError={evaluationQuery.isError}
      onRetry={() => void evaluationQuery.refetch()}
    >
      {evaluationQuery.data && (
        <EvaluationDetailContent evaluationId={evaluationId} evaluation={evaluationQuery.data} />
      )}
    </QueryState>
  );
}

function EvaluationDetailContent({
  evaluationId,
  evaluation,
}: {
  evaluationId: number;
  evaluation: EvaluationOut;
}) {
  const { t } = useTranslation(["common", "evaluations", "approvals"]);
  const localized = useLocalizedField();
  const queryClient = useQueryClient();
  const currentUser = useAuthStore((s) => s.user);
  const [pendingAction, setPendingAction] = useState<Action | null>(null);

  const historyQuery = useQuery({
    queryKey: ["evaluations", evaluationId, "history"],
    queryFn: () => getEvaluationHistory(evaluationId),
    enabled: Number.isFinite(evaluationId),
  });

  const transitionMutation = useMutation({
    mutationFn: ({ action, comment }: { action: Action; comment?: string }) => {
      const fns = { submit: submitEvaluation, approve: approveEvaluation, return: returnEvaluation, review: reviewEvaluation };
      return fns[action](evaluationId, comment);
    },
    onSuccess: () => {
      void message.success(t("evaluations:transitionSuccess"));
      setPendingAction(null);
      void queryClient.invalidateQueries({ queryKey: ["evaluations", evaluationId] });
      void queryClient.invalidateQueries({ queryKey: ["evaluations", evaluationId, "history"] });
      void queryClient.invalidateQueries({ queryKey: ["evaluations"] });
    },
    onError: () => void message.error(t("evaluations:transitionFailed")),
  });

  const roles = currentUser?.roles ?? [];
  const isOwner = currentUser !== null && evaluation.owner_user_id === currentUser.id;
  const editable = isOwner && (evaluation.status === "draft" || evaluation.status === "returned");
  const actions = availableActions(evaluation.status, evaluation.kind, roles, isOwner);

  return (
    <div>
      <Typography.Title level={3}>
        <bdi>{localized(evaluation.employee.full_name_en, evaluation.employee.full_name_ar)}</bdi>
      </Typography.Title>

      <Descriptions bordered size="small" column={2} style={{ marginBottom: 16 }}>
        <Descriptions.Item label={t("evaluations:staffNo")}>
          <Ltr>{evaluation.employee.staff_no}</Ltr>
        </Descriptions.Item>
        <Descriptions.Item label={t("common:common.active")}>
          <EvaluationStatusTag status={evaluation.status} />
        </Descriptions.Item>
        <Descriptions.Item label={t("evaluations:kind")}>
          {t(`evaluations:kindValues.${evaluation.kind}`)}
        </Descriptions.Item>
        <Descriptions.Item label={t("evaluations:scorePct")}>
          {evaluation.score_pct ? (
            <Ltr>
              {(Number(evaluation.score_pct) * 100).toFixed(1)}% ({evaluation.grade})
            </Ltr>
          ) : (
            "—"
          )}
        </Descriptions.Item>
      </Descriptions>

      <Row gutter={16}>
        <Col span={16}>
          <Card>
            <EvaluationScoresForm
              evaluation={evaluation}
              editable={editable}
              onSaved={() => void queryClient.invalidateQueries({ queryKey: ["evaluations", evaluationId] })}
            />

            {actions.length > 0 && (
              <Space style={{ marginTop: 16 }}>
                {actions.map((action) => (
                  <Button
                    key={action}
                    type={action === "return" ? "default" : "primary"}
                    danger={action === "return"}
                    onClick={() => setPendingAction(action)}
                  >
                    {t(`approvals:actions.${action}`)}
                  </Button>
                ))}
              </Space>
            )}
            {actions.length === 0 && (
              <Alert style={{ marginTop: 16 }} type="info" showIcon message={t("evaluations:noActionsAvailable")} />
            )}
          </Card>
        </Col>
        <Col span={8}>
          <Card title={t("approvals:timeline.title")}>
            <ApprovalTimeline history={historyQuery.data ?? []} />
          </Card>
        </Col>
      </Row>

      {pendingAction && (
        <ApprovalActionModal
          action={pendingAction}
          open
          loading={transitionMutation.isPending}
          requireComment={pendingAction === "return"}
          onCancel={() => setPendingAction(null)}
          onConfirm={(comment) => transitionMutation.mutate({ action: pendingAction, comment })}
        />
      )}
    </div>
  );
}

export default EvaluationDetailPage;
