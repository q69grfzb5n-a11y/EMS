import { Table, Typography } from "antd";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { listPendingApprovals } from "@/modules/evaluations/api/evaluationsApi";
import { EvaluationStatusTag } from "@/modules/evaluations/components/EvaluationScoresForm";
import type { EvaluationOut } from "@/modules/evaluations/types";
import { useLocalizedField } from "@/shared/hooks/useLocalizedField";
import { Ltr } from "@/shared/ui/Ltr";

export function ApprovalsInboxPage() {
  const { t } = useTranslation(["common", "approvals", "evaluations"]);
  const navigate = useNavigate();
  const localized = useLocalizedField();
  const query = useQuery({ queryKey: ["approvals", "pending"], queryFn: listPendingApprovals });

  return (
    <div>
      <Typography.Title level={3}>{t("approvals:inbox.title")}</Typography.Title>
      <Table<EvaluationOut>
        rowKey="id"
        loading={query.isLoading}
        dataSource={query.data ?? []}
        pagination={{ pageSize: 50 }}
        onRow={(record) => ({
          onClick: () => navigate(`/evaluations/${record.id}`),
          style: { cursor: "pointer" },
        })}
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
            title: t("evaluations:kind"),
            key: "kind",
            render: (_: unknown, e: EvaluationOut) => t(`evaluations:kindValues.${e.kind}`),
          },
          {
            title: t("common:common.active"),
            key: "status",
            render: (_: unknown, e: EvaluationOut) => <EvaluationStatusTag status={e.status} />,
          },
        ]}
      />
    </div>
  );
}

export default ApprovalsInboxPage;
