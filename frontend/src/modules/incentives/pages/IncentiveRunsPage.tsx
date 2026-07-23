import { useState } from "react";
import { Alert, Button, Form, Modal, Select, Space, Typography, message } from "antd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { isAxiosError } from "axios";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { listPeriods } from "@/modules/attendance/api/attendanceApi";
import { createRun, listRuns } from "@/modules/incentives/api/incentivesApi";
import { IncentiveRunStatusTag } from "@/modules/incentives/components/IncentiveRunStatusTag";
import type { FormulaMode, IncentiveRunOut } from "@/modules/incentives/types";
import { Can } from "@/shared/auth/Can";
import { DataTable } from "@/shared/ui/DataTable";
import { Ltr } from "@/shared/ui/Ltr";

interface CreateFormValues {
  period_id: number;
  formula_mode: FormulaMode;
}

export function IncentiveRunsPage() {
  const { t } = useTranslation(["common", "incentives"]);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [periodId, setPeriodId] = useState<number | null>(null);
  const [createOpen, setCreateOpen] = useState(false);

  const periodsQuery = useQuery({ queryKey: ["attendance", "periods"], queryFn: listPeriods });
  const runsQuery = useQuery({
    queryKey: ["incentive-runs", periodId],
    queryFn: () => listRuns(periodId ?? undefined),
  });

  const createMutation = useMutation({
    mutationFn: (values: CreateFormValues) => createRun(values),
    onSuccess: (run) => {
      void message.success(t("incentives:createSuccess"));
      setCreateOpen(false);
      void queryClient.invalidateQueries({ queryKey: ["incentive-runs"] });
      navigate(`/incentives/${run.id}`);
    },
    onError: (err: unknown) => {
      const code =
        isAxiosError(err) && typeof err.response?.data?.error?.code === "string"
          ? (err.response.data.error.code as string)
          : "unknown_error";
      void message.error(
        t(`incentives:errors.${code}`, { defaultValue: t("incentives:errors.unknown_error") }),
      );
    },
  });

  return (
    <div>
      <Space style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <Typography.Title level={3} style={{ margin: 0 }}>
          {t("incentives:title")}
        </Typography.Title>
        <Can permission="CREATE_INCENTIVE_RUNS">
          <Button type="primary" onClick={() => setCreateOpen(true)}>
            {t("incentives:createRun")}
          </Button>
        </Can>
      </Space>

      <Select
        style={{ minWidth: 220, marginBottom: 16 }}
        placeholder={t("attendance:period", { ns: "attendance" })}
        allowClear
        value={periodId ?? undefined}
        onChange={(v) => setPeriodId(v ?? null)}
        options={(periodsQuery.data ?? []).map((p) => ({
          value: p.id,
          label: `${String(p.month).padStart(2, "0")}-${p.year}`,
        }))}
      />

      {runsQuery.isError && (
        <Alert
          type="error"
          showIcon
          message={t("common:common.loadError")}
          style={{ marginBottom: 16 }}
          action={
            <Button size="small" onClick={() => void runsQuery.refetch()}>
              {t("common:common.retry")}
            </Button>
          }
        />
      )}

      <DataTable<IncentiveRunOut>
        rowKey="id"
        loading={runsQuery.isLoading}
        dataSource={runsQuery.data ?? []}
        searchableText={(r) => [String(r.run_no), r.status]}
        onRow={(record) => ({
          onClick: () => navigate(`/incentives/${record.id}`),
          style: { cursor: "pointer" },
        })}
        columns={[
          { title: t("incentives:runNo"), dataIndex: "run_no", width: 90 },
          {
            title: t("incentives:formulaMode"),
            key: "formula_mode",
            render: (_: unknown, r: IncentiveRunOut) =>
              t(`incentives:formulaModeValues.${r.params.formula_mode}`),
          },
          {
            title: t("common:common.active"),
            key: "status",
            render: (_: unknown, r: IncentiveRunOut) => <IncentiveRunStatusTag status={r.status} />,
          },
          {
            title: t("incentives:lineCount"),
            key: "lines",
            render: (_: unknown, r: IncentiveRunOut) => r.lines.length,
          },
          {
            title: t("incentives:exceptionCount"),
            key: "exceptions",
            render: (_: unknown, r: IncentiveRunOut) => r.exceptions.length,
          },
          {
            title: t("incentives:totalFinalAmount"),
            key: "total",
            render: (_: unknown, r: IncentiveRunOut) => <Ltr>{r.total_final_amount}</Ltr>,
          },
        ]}
      />

      <Modal
        title={t("incentives:createRun")}
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        footer={null}
        destroyOnHidden
      >
        <Form<CreateFormValues>
          layout="vertical"
          initialValues={{ formula_mode: "legacy_flat" }}
          onFinish={(values) => createMutation.mutate(values)}
        >
          <Form.Item
            name="period_id"
            label={t("attendance:period", { ns: "attendance" })}
            rules={[{ required: true }]}
          >
            <Select
              options={(periodsQuery.data ?? []).map((p) => ({
                value: p.id,
                label: `${String(p.month).padStart(2, "0")}-${p.year}`,
              }))}
            />
          </Form.Item>
          <Form.Item
            name="formula_mode"
            label={t("incentives:formulaMode")}
            rules={[{ required: true }]}
          >
            <Select
              options={[
                { value: "legacy_flat", label: t("incentives:formulaModeValues.legacy_flat") },
                { value: "pct_of_salary", label: t("incentives:formulaModeValues.pct_of_salary") },
              ]}
            />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={createMutation.isPending} block>
              {t("common:common.create")}
            </Button>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

export default IncentiveRunsPage;
