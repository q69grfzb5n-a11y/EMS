import { useState } from "react";
import { Button, DatePicker, Form, Input, Modal, Select, Space, Table, Typography, message } from "antd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { isAxiosError } from "axios";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import dayjs from "dayjs";

import { listEmployees } from "@/modules/employees/api/employeesApi";
import { listDepartments } from "@/modules/org/api/orgApi";
import { createTransfer, listTransfers, submitTransfer } from "@/modules/transfers/api/transfersApi";
import { TransferStatusTag } from "@/modules/transfers/components/TransferStatusTag";
import type { TransferRequestOut } from "@/modules/transfers/types";
import { Can } from "@/shared/auth/Can";
import { useAuthStore } from "@/shared/auth/authStore";
import { useLocalizedField } from "@/shared/hooks/useLocalizedField";
import { Ltr } from "@/shared/ui/Ltr";

interface CreateFormValues {
  employee_id: number;
  to_department_id: number;
  effective_date: dayjs.Dayjs;
  reason?: string;
}

export function TransferRequestsPage() {
  const { t } = useTranslation(["common", "transfers", "approvals"]);
  const navigate = useNavigate();
  const localized = useLocalizedField();
  const queryClient = useQueryClient();
  const currentUser = useAuthStore((s) => s.user);
  const [createOpen, setCreateOpen] = useState(false);

  const transfersQuery = useQuery({ queryKey: ["transfers"], queryFn: listTransfers });
  const employeesQuery = useQuery({ queryKey: ["employees"], queryFn: listEmployees });
  const departmentsQuery = useQuery({ queryKey: ["org", "departments"], queryFn: listDepartments });

  const submitMutation = useMutation({
    mutationFn: (id: number) => submitTransfer(id),
    onSuccess: () => {
      void message.success(t("approvals:actions.submit", { ns: "approvals" }));
      void queryClient.invalidateQueries({ queryKey: ["transfers"] });
    },
  });

  const createMutation = useMutation({
    mutationFn: (values: CreateFormValues) =>
      createTransfer({
        employee_id: values.employee_id,
        to_department_id: values.to_department_id,
        effective_date: values.effective_date.format("YYYY-MM-DD"),
        reason: values.reason ?? null,
      }),
    onSuccess: () => {
      void message.success(t("transfers:createSuccess"));
      setCreateOpen(false);
      void queryClient.invalidateQueries({ queryKey: ["transfers"] });
    },
    onError: (err: unknown) => {
      const code =
        isAxiosError(err) && typeof err.response?.data?.error?.code === "string"
          ? (err.response.data.error.code as string)
          : "unknown_error";
      void message.error(t(`transfers:errors.${code}`, { defaultValue: t("transfers:errors.unknown_error") }));
    },
  });

  return (
    <div>
      <Space style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <Typography.Title level={3} style={{ margin: 0 }}>
          {t("transfers:title")}
        </Typography.Title>
        <Can permission="REQUEST_TRANSFERS">
          <Button type="primary" onClick={() => setCreateOpen(true)}>
            {t("transfers:requestTransfer")}
          </Button>
        </Can>
      </Space>

      <Table<TransferRequestOut>
        rowKey="id"
        loading={transfersQuery.isLoading}
        dataSource={transfersQuery.data ?? []}
        pagination={{ pageSize: 50 }}
        columns={[
          {
            title: t("transfers:staffNo"),
            key: "staff_no",
            render: (_: unknown, r: TransferRequestOut) => <Ltr>{r.employee.staff_no}</Ltr>,
          },
          {
            title: t("transfers:employeeName"),
            key: "name",
            render: (_: unknown, r: TransferRequestOut) => (
              <bdi>{localized(r.employee.full_name_en, r.employee.full_name_ar)}</bdi>
            ),
          },
          {
            title: t("transfers:fromDepartment"),
            key: "from",
            render: (_: unknown, r: TransferRequestOut) => (
              <bdi>{localized(r.from_department.name_en, r.from_department.name_ar)}</bdi>
            ),
          },
          {
            title: t("transfers:toDepartment"),
            key: "to",
            render: (_: unknown, r: TransferRequestOut) => (
              <bdi>{localized(r.to_department.name_en, r.to_department.name_ar)}</bdi>
            ),
          },
          {
            title: t("transfers:effectiveDate"),
            key: "effective_date",
            render: (_: unknown, r: TransferRequestOut) => <Ltr>{r.effective_date}</Ltr>,
          },
          {
            title: t("common:common.active"),
            key: "status",
            render: (_: unknown, r: TransferRequestOut) => <TransferStatusTag status={r.status} />,
          },
          {
            title: t("common:common.edit"),
            key: "actions",
            render: (_: unknown, r: TransferRequestOut) => {
              const isRequester = currentUser !== null && r.requested_by_user_id === currentUser.id;
              const canSubmit = isRequester && (r.status === "draft" || r.status === "returned");
              return (
                <Space>
                  <Button size="small" onClick={() => navigate(`/transfers/${r.id}`)}>
                    {t("evaluations:bulkEntry.open", { ns: "evaluations" })}
                  </Button>
                  {canSubmit && (
                    <Button
                      size="small"
                      type="primary"
                      loading={submitMutation.isPending}
                      onClick={() => submitMutation.mutate(r.id)}
                    >
                      {t("approvals:actions.submit", { ns: "approvals" })}
                    </Button>
                  )}
                </Space>
              );
            },
          },
        ]}
      />

      <Modal
        title={t("transfers:requestTransfer")}
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        footer={null}
        destroyOnHidden
      >
        <Form<CreateFormValues>
          layout="vertical"
          onFinish={(values) => createMutation.mutate(values)}
          initialValues={{ effective_date: dayjs().add(1, "month").startOf("month") }}
        >
          <Form.Item name="employee_id" label={t("transfers:employee")} rules={[{ required: true }]}>
            <Select
              showSearch
              optionFilterProp="label"
              options={(employeesQuery.data ?? []).map((e) => ({
                value: e.id,
                label: `${e.staff_no} — ${localized(e.full_name_en, e.full_name_ar)}`,
              }))}
            />
          </Form.Item>
          <Form.Item
            name="to_department_id"
            label={t("transfers:toDepartment")}
            rules={[{ required: true }]}
          >
            <Select
              options={(departmentsQuery.data ?? []).map((d) => ({
                value: d.id,
                label: `${d.code} — ${localized(d.name_en, d.name_ar)}`,
              }))}
            />
          </Form.Item>
          <Form.Item
            name="effective_date"
            label={t("transfers:effectiveDate")}
            rules={[{ required: true }]}
          >
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="reason" label={t("transfers:reason")}>
            <Input.TextArea rows={3} />
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

export default TransferRequestsPage;
