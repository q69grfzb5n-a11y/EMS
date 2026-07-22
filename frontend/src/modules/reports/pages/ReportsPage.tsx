import { useState } from "react";
import { Alert, Button, Card, Descriptions, Select, Space, Table, Typography, message } from "antd";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { listPeriods } from "@/modules/attendance/api/attendanceApi";
import {
  downloadFinanceExcel,
  downloadFinancePdf,
  getPeriodSummary,
} from "@/modules/reports/api/reportsApi";
import type { DeptSummaryOut } from "@/modules/reports/types";
import { useLocalizedField } from "@/shared/hooks/useLocalizedField";
import { Ltr } from "@/shared/ui/Ltr";
import { triggerBlobDownload } from "@/shared/utils/download";

export function ReportsPage() {
  const { t } = useTranslation(["common", "reports"]);
  const localized = useLocalizedField();
  const [periodId, setPeriodId] = useState<number | null>(null);

  const periodsQuery = useQuery({ queryKey: ["attendance", "periods"], queryFn: listPeriods });
  const summaryQuery = useQuery({
    queryKey: ["reports", "period-summary", periodId],
    queryFn: () => getPeriodSummary(periodId as number),
    enabled: periodId !== null,
  });

  const excelMutation = useMutation({
    mutationFn: () => downloadFinanceExcel(summaryQuery.data!.run_id as number),
    onSuccess: (blob) => {
      triggerBlobDownload(blob, `incentive_payout_run_${summaryQuery.data?.run_id}.xlsx`);
    },
    onError: () => void message.error(t("reports:downloadFailed")),
  });

  const pdfMutation = useMutation({
    mutationFn: () => downloadFinancePdf(summaryQuery.data!.run_id as number),
    onSuccess: (blob) => {
      triggerBlobDownload(blob, `incentive_summary_run_${summaryQuery.data?.run_id}.pdf`);
    },
    onError: () => void message.error(t("reports:downloadFailed")),
  });

  const summary = summaryQuery.data;
  const hasApprovedRun = summary?.run_status === "approved";

  return (
    <div>
      <Typography.Title level={3}>{t("reports:title")}</Typography.Title>

      <Select
        style={{ minWidth: 220, marginBottom: 16 }}
        placeholder={t("attendance:period", { ns: "attendance" })}
        value={periodId ?? undefined}
        onChange={setPeriodId}
        options={(periodsQuery.data ?? []).map((p) => ({
          value: p.id,
          label: `${String(p.month).padStart(2, "0")}-${p.year}`,
        }))}
      />

      {periodId !== null && summary && !hasApprovedRun && (
        <Alert type="info" showIcon message={t("reports:noApprovedRun")} />
      )}

      {periodId !== null && summary && (
        <Card
          style={{ marginTop: 16 }}
          title={t("reports:periodSummary")}
          extra={
            hasApprovedRun && (
              <Space>
                <Button loading={excelMutation.isPending} onClick={() => excelMutation.mutate()}>
                  {t("reports:downloadExcel")}
                </Button>
                <Button loading={pdfMutation.isPending} onClick={() => pdfMutation.mutate()}>
                  {t("reports:downloadPdf")}
                </Button>
              </Space>
            )
          }
        >
          <Descriptions size="small" column={2} style={{ marginBottom: 16 }}>
            <Descriptions.Item label={t("reports:grandTotal")}>
              <Ltr>{summary.grand_total}</Ltr>
            </Descriptions.Item>
          </Descriptions>

          <Table<DeptSummaryOut>
            rowKey="department_id"
            size="small"
            pagination={false}
            dataSource={summary.departments}
            columns={[
              {
                title: t("incentives:department", { ns: "incentives" }),
                key: "name",
                render: (_: unknown, d: DeptSummaryOut) => (
                  <bdi>{localized(d.name_en, d.name_ar)}</bdi>
                ),
              },
              {
                title: t("incentives:lineCount", { ns: "incentives" }),
                dataIndex: "employee_count",
              },
              {
                title: t("incentives:totalFinalAmount", { ns: "incentives" }),
                key: "total",
                render: (_: unknown, d: DeptSummaryOut) => <Ltr>{d.total_amount}</Ltr>,
              },
            ]}
          />
        </Card>
      )}
    </div>
  );
}

export default ReportsPage;
