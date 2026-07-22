import { Card, Statistic } from "antd";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { listPendingApprovals } from "@/modules/approvals/api/approvalsApi";

export function PendingApprovalsCard() {
  const { t } = useTranslation(["common", "dashboard"]);
  const navigate = useNavigate();
  const query = useQuery({ queryKey: ["approvals", "pending"], queryFn: listPendingApprovals });

  return (
    <Card
      title={t("dashboard:pendingApprovals.title")}
      loading={query.isLoading}
      hoverable
      onClick={() => navigate("/approvals")}
    >
      <Statistic value={query.data?.length ?? 0} />
    </Card>
  );
}

export default PendingApprovalsCard;
