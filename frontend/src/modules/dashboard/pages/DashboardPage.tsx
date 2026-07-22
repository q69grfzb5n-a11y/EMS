import { Col, Row, Typography } from "antd";
import { useTranslation } from "react-i18next";

import { DeptTotalsChart } from "@/modules/dashboard/components/DeptTotalsChart";
import { MonthStatusCard } from "@/modules/dashboard/components/MonthStatusCard";
import { MyIncentiveCard } from "@/modules/dashboard/components/MyIncentiveCard";
import { PendingApprovalsCard } from "@/modules/dashboard/components/PendingApprovalsCard";
import { Can } from "@/shared/auth/Can";

export function DashboardPage() {
  const { t } = useTranslation();

  return (
    <div>
      <Typography.Title level={3}>{t("nav.dashboard")}</Typography.Title>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={8}>
          <MyIncentiveCard />
        </Col>
        <Col xs={24} sm={12} md={8}>
          <PendingApprovalsCard />
        </Col>
        <Col xs={24} sm={12} md={8}>
          <MonthStatusCard />
        </Col>
        <Can permission="VIEW_FINANCE_REPORTS">
          <Col xs={24}>
            <DeptTotalsChart />
          </Col>
        </Can>
      </Row>
    </div>
  );
}

export default DashboardPage;
