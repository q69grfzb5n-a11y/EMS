import { useState } from "react";
import { Alert, Button, Card, Col, Descriptions, Row, Space, Typography, message } from "antd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";

import { ApprovalActionModal } from "@/modules/approvals/components/ApprovalActionModal";
import { ApprovalTimeline } from "@/modules/approvals/components/ApprovalTimeline";
import {
  approveTransfer,
  getTransfer,
  getTransferHistory,
  returnTransfer,
  reviewTransfer,
  submitTransfer,
} from "@/modules/transfers/api/transfersApi";
import { TransferStatusTag } from "@/modules/transfers/components/TransferStatusTag";
import { useAuthStore } from "@/shared/auth/authStore";
import { useLocalizedField } from "@/shared/hooks/useLocalizedField";
import { Ltr } from "@/shared/ui/Ltr";

type Action = "submit" | "approve" | "return" | "review";

function availableActions(status: string, roles: string[], isRequester: boolean): Action[] {
  const actions: Action[] = [];
  if ((status === "draft" || status === "returned") && isRequester) {
    actions.push("submit");
  }
  if (status === "submitted" && roles.includes("pmo")) {
    actions.push("review", "return");
  }
  if (status === "pmo_reviewed" && roles.includes("factory_manager")) {
    actions.push("approve", "return");
  }
  return actions;
}

export function TransferDetailPage() {
  const { id } = useParams<{ id: string }>();
  const transferId = Number(id);
  const { t } = useTranslation(["common", "transfers", "approvals"]);
  const localized = useLocalizedField();
  const queryClient = useQueryClient();
  const currentUser = useAuthStore((s) => s.user);
  const [pendingAction, setPendingAction] = useState<Action | null>(null);

  const transferQuery = useQuery({
    queryKey: ["transfers", transferId],
    queryFn: () => getTransfer(transferId),
    enabled: Number.isFinite(transferId),
  });
  const historyQuery = useQuery({
    queryKey: ["transfers", transferId, "history"],
    queryFn: () => getTransferHistory(transferId),
    enabled: Number.isFinite(transferId),
  });

  const transitionMutation = useMutation({
    mutationFn: ({ action, comment }: { action: Action; comment?: string }) => {
      const fns = { submit: submitTransfer, approve: approveTransfer, return: returnTransfer, review: reviewTransfer };
      return fns[action](transferId, comment);
    },
    onSuccess: () => {
      void message.success(t("evaluations:transitionSuccess", { ns: "evaluations" }));
      setPendingAction(null);
      void queryClient.invalidateQueries({ queryKey: ["transfers", transferId] });
      void queryClient.invalidateQueries({ queryKey: ["transfers", transferId, "history"] });
      void queryClient.invalidateQueries({ queryKey: ["transfers"] });
    },
    onError: () => void message.error(t("evaluations:transitionFailed", { ns: "evaluations" })),
  });

  if (!transferQuery.data) return null;
  const transfer = transferQuery.data;
  const roles = currentUser?.roles ?? [];
  const isRequester = currentUser !== null && transfer.requested_by_user_id === currentUser.id;
  const actions = availableActions(transfer.status, roles, isRequester);

  return (
    <div>
      <Typography.Title level={3}>
        <bdi>{localized(transfer.employee.full_name_en, transfer.employee.full_name_ar)}</bdi>
      </Typography.Title>

      <Row gutter={16}>
        <Col span={16}>
          <Card>
            <Descriptions bordered size="small" column={2} style={{ marginBottom: 16 }}>
              <Descriptions.Item label={t("transfers:staffNo")}>
                <Ltr>{transfer.employee.staff_no}</Ltr>
              </Descriptions.Item>
              <Descriptions.Item label={t("common:common.active")}>
                <TransferStatusTag status={transfer.status} />
              </Descriptions.Item>
              <Descriptions.Item label={t("transfers:fromDepartment")}>
                <bdi>{localized(transfer.from_department.name_en, transfer.from_department.name_ar)}</bdi>
              </Descriptions.Item>
              <Descriptions.Item label={t("transfers:toDepartment")}>
                <bdi>{localized(transfer.to_department.name_en, transfer.to_department.name_ar)}</bdi>
              </Descriptions.Item>
              <Descriptions.Item label={t("transfers:effectiveDate")}>
                <Ltr>{transfer.effective_date}</Ltr>
              </Descriptions.Item>
              <Descriptions.Item label={t("transfers:reason")} span={2}>
                {transfer.reason ?? "—"}
              </Descriptions.Item>
            </Descriptions>

            {actions.length > 0 && (
              <Space>
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
              <Alert
                type="info"
                showIcon
                message={t("evaluations:noActionsAvailable", { ns: "evaluations" })}
              />
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

export default TransferDetailPage;
