import { useState } from "react";
import { Button, Form, Input, Modal, Table, Tag, Typography, message } from "antd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { listZeroFlags, overrideZeroFlag } from "@/modules/attendance/api/attendanceApi";
import type { AttendanceZeroFlagOut } from "@/modules/attendance/types";
import { Can } from "@/shared/auth/Can";
import { Ltr } from "@/shared/ui/Ltr";

export function ZeroFlagsPage() {
  const { t } = useTranslation(["common", "attendance"]);
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["attendance", "zero-flags"], queryFn: () => listZeroFlags() });
  const [overrideTarget, setOverrideTarget] = useState<AttendanceZeroFlagOut | null>(null);

  const overrideMutation = useMutation({
    mutationFn: ({ id, reason }: { id: number; reason: string }) => overrideZeroFlag(id, reason),
    onSuccess: () => {
      void message.success(t("attendance:zeroFlags.overridden"));
      setOverrideTarget(null);
      void queryClient.invalidateQueries({ queryKey: ["attendance", "zero-flags"] });
    },
  });

  return (
    <div>
      <Typography.Title level={3}>{t("attendance:zeroFlags.title")}</Typography.Title>
      <Typography.Paragraph type="secondary">
        {t("attendance:zeroFlags.description")}
      </Typography.Paragraph>

      <Table<AttendanceZeroFlagOut>
        rowKey="id"
        loading={query.isLoading}
        dataSource={query.data ?? []}
        pagination={{ pageSize: 20 }}
        columns={[
          {
            title: t("attendance:zeroFlags.employeeId"),
            dataIndex: "employee_id",
            render: (v: number) => <Ltr>{v}</Ltr>,
          },
          {
            title: t("attendance:zeroFlags.window"),
            key: "window",
            render: (_: unknown, f: AttendanceZeroFlagOut) => (
              <Ltr>
                #{f.period_from_id} → #{f.period_to_id}
              </Ltr>
            ),
          },
          {
            title: t("attendance:zeroFlags.totalDays"),
            key: "total",
            render: (_: unknown, f: AttendanceZeroFlagOut) => (
              <Ltr>
                {f.total_leave_absence_days} / {f.allowance_days}
              </Ltr>
            ),
          },
          {
            title: t("common:common.active"),
            dataIndex: "is_overridden",
            render: (v: boolean, f: AttendanceZeroFlagOut) =>
              v ? (
                <Tag color="blue" title={f.override_reason ?? undefined}>
                  {t("attendance:zeroFlags.overriddenTag")}
                </Tag>
              ) : (
                <Tag color="red">{t("attendance:zeroFlags.activeTag")}</Tag>
              ),
          },
          {
            title: t("common:common.edit"),
            key: "actions",
            render: (_: unknown, f: AttendanceZeroFlagOut) =>
              !f.is_overridden && (
                <Can permission="MANAGE_ATTENDANCE">
                  <Button size="small" onClick={() => setOverrideTarget(f)}>
                    {t("attendance:zeroFlags.override")}
                  </Button>
                </Can>
              ),
          },
        ]}
      />

      {overrideTarget && (
        <Modal
          title={t("attendance:zeroFlags.override")}
          open
          onCancel={() => setOverrideTarget(null)}
          footer={null}
          destroyOnHidden
        >
          <Form
            layout="vertical"
            onFinish={(values: { reason: string }) =>
              overrideMutation.mutate({ id: overrideTarget.id, reason: values.reason })
            }
          >
            <Form.Item
              name="reason"
              label={t("attendance:zeroFlags.reason")}
              rules={[{ required: true }]}
            >
              <Input.TextArea rows={3} />
            </Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit" loading={overrideMutation.isPending} block>
                {t("common:common.save")}
              </Button>
            </Form.Item>
          </Form>
        </Modal>
      )}
    </div>
  );
}

export default ZeroFlagsPage;
