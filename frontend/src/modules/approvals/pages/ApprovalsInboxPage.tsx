import { Table, Tag, Typography } from "antd";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { listPendingApprovals } from "@/modules/approvals/api/approvalsApi";
import { EvaluationStatusTag } from "@/modules/evaluations/components/EvaluationScoresForm";
import { TransferStatusTag } from "@/modules/transfers/components/TransferStatusTag";
import type { PendingItemOut } from "@/shared/types/approvals";
import { useLocalizedField } from "@/shared/hooks/useLocalizedField";
import { Ltr } from "@/shared/ui/Ltr";

export function ApprovalsInboxPage() {
  const { t } = useTranslation(["common", "approvals", "evaluations", "transfers"]);
  const navigate = useNavigate();
  const localized = useLocalizedField();
  const query = useQuery({ queryKey: ["approvals", "pending"], queryFn: listPendingApprovals });

  return (
    <div>
      <Typography.Title level={3}>{t("approvals:inbox.title")}</Typography.Title>
      <Table<PendingItemOut>
        rowKey={(record) => `${record.entity_type}-${record.id}`}
        loading={query.isLoading}
        dataSource={query.data ?? []}
        pagination={{ pageSize: 50 }}
        onRow={(record) => ({
          onClick: () => navigate(`/${record.entity_type === "evaluation" ? "evaluations" : "transfers"}/${record.id}`),
          style: { cursor: "pointer" },
        })}
        columns={[
          {
            title: t("evaluations:staffNo"),
            key: "staff_no",
            render: (_: unknown, i: PendingItemOut) => <Ltr>{i.employee.staff_no}</Ltr>,
          },
          {
            title: t("evaluations:employeeName"),
            key: "name",
            render: (_: unknown, i: PendingItemOut) => (
              <bdi>{localized(i.employee.full_name_en, i.employee.full_name_ar)}</bdi>
            ),
          },
          {
            title: t("evaluations:kind"),
            key: "kind",
            render: (_: unknown, i: PendingItemOut) =>
              i.entity_type === "evaluation" ? (
                t(`evaluations:kindValues.${i.kind}`)
              ) : (
                <Tag>{t("transfers:title")}</Tag>
              ),
          },
          {
            title: t("common:common.active"),
            key: "status",
            render: (_: unknown, i: PendingItemOut) =>
              i.entity_type === "evaluation" ? (
                <EvaluationStatusTag status={i.status} />
              ) : (
                <TransferStatusTag status={i.status} />
              ),
          },
        ]}
      />
    </div>
  );
}

export default ApprovalsInboxPage;
