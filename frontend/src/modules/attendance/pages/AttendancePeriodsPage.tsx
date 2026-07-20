import { useState } from "react";
import { Button, Form, InputNumber, Modal, Space, Table, Tag, Typography } from "antd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { createPeriod, listPeriods } from "@/modules/attendance/api/attendanceApi";
import type { IncentivePeriodOut } from "@/modules/attendance/types";
import { Can } from "@/shared/auth/Can";
import { Ltr } from "@/shared/ui/Ltr";

export function AttendancePeriodsPage() {
  const { t } = useTranslation(["common", "attendance"]);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["attendance", "periods"], queryFn: listPeriods });
  const [createOpen, setCreateOpen] = useState(false);

  const createMutation = useMutation({
    mutationFn: createPeriod,
    onSuccess: (period) => {
      setCreateOpen(false);
      void queryClient.invalidateQueries({ queryKey: ["attendance", "periods"] });
      navigate(`/attendance/${period.id}`);
    },
  });

  return (
    <div>
      <Space style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <Typography.Title level={3} style={{ margin: 0 }}>
          {t("attendance:title")}
        </Typography.Title>
        <Space>
          <Button onClick={() => navigate("/attendance/zero-flags")}>
            {t("attendance:zeroFlags.title")}
          </Button>
          <Can permission="MANAGE_PERIODS">
            <Button type="primary" onClick={() => setCreateOpen(true)}>
              {t("attendance:createPeriod")}
            </Button>
          </Can>
        </Space>
      </Space>

      <Table<IncentivePeriodOut>
        rowKey="id"
        loading={query.isLoading}
        dataSource={query.data ?? []}
        pagination={false}
        onRow={(record) => ({
          onClick: () => navigate(`/attendance/${record.id}`),
          style: { cursor: "pointer" },
        })}
        columns={[
          {
            title: t("attendance:period"),
            key: "period",
            render: (_: unknown, p: IncentivePeriodOut) => (
              <Ltr>
                {String(p.month).padStart(2, "0")}-{p.year}
              </Ltr>
            ),
          },
          {
            title: t("common:common.active"),
            dataIndex: "status",
            render: (v: string) => (
              <Tag color={v === "open" ? "green" : "default"}>
                {t(`attendance:periodStatus.${v}`)}
              </Tag>
            ),
          },
        ]}
      />

      <Modal
        title={t("attendance:createPeriod")}
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        footer={null}
        destroyOnHidden
      >
        <Form layout="vertical" onFinish={(values) => createMutation.mutate(values)}>
          <Form.Item name="year" label={t("attendance:year")} rules={[{ required: true }]}>
            <InputNumber min={2000} max={2100} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="month" label={t("attendance:month")} rules={[{ required: true }]}>
            <InputNumber min={1} max={12} style={{ width: "100%" }} />
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

export default AttendancePeriodsPage;
