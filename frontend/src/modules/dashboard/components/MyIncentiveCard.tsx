import { Card, Empty, Statistic } from "antd";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { listMyIncentives } from "@/modules/incentives/api/incentivesApi";

export function MyIncentiveCard() {
  const { t } = useTranslation(["common", "dashboard"]);
  const query = useQuery({ queryKey: ["incentive-runs", "my"], queryFn: listMyIncentives });

  const latest = query.data?.[0];

  return (
    <Card title={t("dashboard:myIncentive.title")} loading={query.isLoading}>
      {latest ? (
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
