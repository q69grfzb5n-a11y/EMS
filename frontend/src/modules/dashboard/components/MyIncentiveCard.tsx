import { Alert, Button, Card, Empty, Statistic } from "antd";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { listMyIncentives } from "@/modules/incentives/api/incentivesApi";

export function MyIncentiveCard() {
  const { t } = useTranslation(["common", "dashboard"]);
  const query = useQuery({ queryKey: ["incentive-runs", "my"], queryFn: listMyIncentives });

  const latest = query.data?.[0];

  return (
    <Card title={t("dashboard:myIncentive.title")} loading={query.isLoading}>
      {query.isError ? (
        <Alert
          type="error"
          showIcon
          message={t("common:common.loadError")}
          action={
            <Button size="small" onClick={() => void query.refetch()}>
              {t("common:common.retry")}
            </Button>
          }
        />
      ) : latest ? (
        <Statistic
          value={Number(latest.final_amount)}
          suffix={t("dashboard:myIncentive.currency")}
          precision={2}
        />
      ) : (
        <Empty description={t("dashboard:myIncentive.empty")} />
      )}
    </Card>
  );
}

export default MyIncentiveCard;
