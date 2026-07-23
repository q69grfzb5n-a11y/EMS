import { Alert, Button, Card, Statistic } from "antd";
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
      hoverable={!query.isError}
      onClick={() => !query.isError && navigate("/approvals")}
    >
      {query.isError ? (
        <Alert
          type="error"
          showIcon
          message={t("common:common.loadError")}
          action={
            <Button
              size="small"
              onClick={(e) => {
                e.stopPropagation();
                void query.refetch();
              }}
            >
              {t("common:common.retry")}
            </Button>
          }
        />
      ) : (
        <Statistic value={query.data?.length ?? 0} />
      )}
    </Card>
  );
}

export default PendingApprovalsCard;
