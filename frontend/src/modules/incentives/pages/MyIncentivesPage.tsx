import { Card, Empty, List, Typography } from "antd";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { listMyIncentives } from "@/modules/incentives/api/incentivesApi";
import { IncentiveLineBreakdown } from "@/modules/incentives/components/IncentiveLineBreakdown";
import type { IncentiveLineItemOut } from "@/modules/incentives/types";
import { Ltr } from "@/shared/ui/Ltr";

export function MyIncentivesPage() {
  const { t } = useTranslation(["common", "incentives"]);
  const query = useQuery({ queryKey: ["incentive-runs", "my"], queryFn: listMyIncentives });

  return (
    <div>
      <Typography.Title level={3}>{t("incentives:myIncentives.title")}</Typography.Title>

      {query.data && query.data.length === 0 && (
        <Empty description={t("incentives:myIncentives.empty")} />
      )}

      <List<IncentiveLineItemOut>
        loading={query.isLoading}
        dataSource={query.data ?? []}
        renderItem={(line) => (
          <List.Item>
            <Card
              style={{ width: "100%" }}
              title={<Ltr>{t("incentives:myIncentives.amount", { amount: line.final_amount })}</Ltr>}
            >
              <IncentiveLineBreakdown line={line} />
            </Card>
          </List.Item>
        )}
      />
    </div>
  );
}

export default MyIncentivesPage;
