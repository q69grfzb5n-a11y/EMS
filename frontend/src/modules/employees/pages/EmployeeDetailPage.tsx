import { useState } from "react";
import { Button, Descriptions, Form, Input, InputNumber, Modal, Select, Space, Tabs, Table, Tag, Typography } from "antd";
import { DatePicker } from "antd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";
import dayjs from "dayjs";

import { listUsers } from "@/modules/auth/api/authApi";
import {
  assignReviewer,
  createSalary,
  getEmployee,
  listSalaries,
  patchEmployee,
} from "@/modules/employees/api/employeesApi";
import type { EmployeeOut, EmployeeSalaryOut } from "@/modules/employees/types";
import { listDepartments, listPositions } from "@/modules/org/api/orgApi";
import { useAuthStore } from "@/shared/auth/authStore";
import { hasPermission } from "@/shared/auth/permissions";
import { useLocalizedField } from "@/shared/hooks/useLocalizedField";
import { Ltr } from "@/shared/ui/Ltr";
import { LTR_INPUT_STYLES } from "@/shared/ui/ltrInput";

export function EmployeeDetailPage() {
  const { id } = useParams<{ id: string }>();
  const employeeId = Number(id);
  const { t } = useTranslation(["common", "employees", "org"]);
  const localized = useLocalizedField();
  const canViewSalary = useAuthStore((s) => hasPermission(s.user?.roles ?? [], "VIEW_SALARY"));
  const canManageEmployees = useAuthStore((s) => hasPermission(s.user?.roles ?? [], "MANAGE_EMPLOYEES"));

  const employeeQuery = useQuery({
    queryKey: ["employees", employeeId],
    queryFn: () => getEmployee(employeeId),
    enabled: Number.isFinite(employeeId),
  });

  if (employeeQuery.isLoading || !employeeQuery.data) {
    return null;
  }
  const employee = employeeQuery.data;

  const items = [
    {
      key: "overview",
      label: t("employees:tabs.overview"),
      children: <OverviewTab employee={employee} canEdit={canManageEmployees} />,
    },
  ];

  if (canManageEmployees) {
    items.push({
      key: "reviewer",
      label: t("employees:tabs.reviewer"),
      children: <ReviewerTab employeeId={employee.id} currentReviewerId={employee.reviewer_user_id} />,
    });
  }

  if (canViewSalary) {
    items.push({
      key: "salary",
      label: t("employees:tabs.salary"),
      children: <SalaryTab employeeId={employee.id} />,
    });
  }

  return (
    <div>
      <Typography.Title level={3}>
        <bdi>{localized(employee.full_name_en, employee.full_name_ar)}</bdi>
      </Typography.Title>
      <Tabs items={items} />
    </div>
  );
}

function OverviewTab({ employee, canEdit }: { employee: EmployeeOut; canEdit: boolean }) {
  const { t } = useTranslation(["common", "employees"]);
  const localized = useLocalizedField();
  const queryClient = useQueryClient();
  const [editOpen, setEditOpen] = useState(false);
  const departmentsQuery = useQuery({ queryKey: ["org", "departments"], queryFn: listDepartments });
  const positionsQuery = useQuery({ queryKey: ["org", "positions"], queryFn: listPositions });

  const patchMutation = useMutation({
    mutationFn: (payload: {
      full_name_ar: string;
      full_name_en?: string;
      department_id: number;
      position_id: number;
      contract_position_title?: string;
    }) => patchEmployee(employee.id, payload),
    onSuccess: () => {
      setEditOpen(false);
      void queryClient.invalidateQueries({ queryKey: ["employees", employee.id] });
      void queryClient.invalidateQueries({ queryKey: ["employees"] });
    },
  });

  return (
    <div>
      {canEdit && (
        <Space style={{ display: "flex", justifyContent: "flex-end", marginBottom: 12 }}>
          <Button onClick={() => setEditOpen(true)}>{t("common:common.edit")}</Button>
        </Space>
      )}
      <Descriptions bordered column={1} size="middle">
        <Descriptions.Item label={t("employees:staffNo")}><Ltr>{employee.staff_no}</Ltr></Descriptions.Item>
        <Descriptions.Item label={t("employees:nameAr")}><bdi>{employee.full_name_ar}</bdi></Descriptions.Item>
        <Descriptions.Item label={t("employees:nameEn")}>
          {employee.full_name_en ? <bdi>{employee.full_name_en}</bdi> : "—"}
        </Descriptions.Item>
        <Descriptions.Item label={t("employees:department")}>
          <bdi>{localized(employee.department.name_en, employee.department.name_ar)}</bdi>
        </Descriptions.Item>
        <Descriptions.Item label={t("employees:position")}>
          <bdi>{localized(employee.position.title_en, employee.position.title_ar)}</bdi>
        </Descriptions.Item>
        <Descriptions.Item label={t("employees:contractTitle")}>
          {employee.contract_position_title ? <bdi>{employee.contract_position_title}</bdi> : "—"}
        </Descriptions.Item>
        <Descriptions.Item label={t("employees:status")}>
          <Tag color={employee.employment_status === "active" ? "green" : "default"}>
            {t(`employees:statusValues.${employee.employment_status}`)}
          </Tag>
        </Descriptions.Item>
      </Descriptions>

      {editOpen && (
        <Modal
          title={t("common:common.edit")}
          open
          onCancel={() => setEditOpen(false)}
          footer={null}
          destroyOnHidden
        >
          <Form
            layout="vertical"
            initialValues={{
              full_name_ar: employee.full_name_ar,
              full_name_en: employee.full_name_en ?? undefined,
              department_id: employee.department.id,
              position_id: employee.position.id,
              contract_position_title: employee.contract_position_title ?? undefined,
            }}
            onFinish={(values) => patchMutation.mutate(values)}
          >
            <Form.Item name="full_name_ar" label={t("employees:nameAr")} rules={[{ required: true }]}>
              <Input />
            </Form.Item>
            <Form.Item name="full_name_en" label={t("employees:nameEn")}>
              <Input dir="ltr" styles={LTR_INPUT_STYLES} />
            </Form.Item>
            <Form.Item name="department_id" label={t("employees:department")} rules={[{ required: true }]}>
              <Select
                options={(departmentsQuery.data ?? []).map((d) => ({
                  value: d.id,
                  label: `${d.code} — ${localized(d.name_en, d.name_ar)}`,
                }))}
              />
            </Form.Item>
            <Form.Item name="position_id" label={t("employees:position")} rules={[{ required: true }]}>
              <Select
                showSearch
                optionFilterProp="label"
                options={(positionsQuery.data ?? []).map((p) => ({
                  value: p.id,
                  label: `${p.code} — ${localized(p.title_en, p.title_ar)}`,
                }))}
              />
            </Form.Item>
            <Form.Item name="contract_position_title" label={t("employees:contractTitle")}>
              <Input />
            </Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit" loading={patchMutation.isPending} block>
                {t("common:common.save")}
              </Button>
            </Form.Item>
          </Form>
        </Modal>
      )}
    </div>
  );
}

function ReviewerTab({ employeeId, currentReviewerId }: { employeeId: number; currentReviewerId: number | null }) {
  const { t } = useTranslation(["common", "employees"]);
  const queryClient = useQueryClient();
  const usersQuery = useQuery({ queryKey: ["users"], queryFn: listUsers });

  const mutation = useMutation({
    mutationFn: (reviewerUserId: number) => assignReviewer(employeeId, reviewerUserId),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["employees", employeeId] }),
  });

  return (
    <Space direction="vertical">
      <Typography.Text>{t("employees:reviewer.current")}: {currentReviewerId ?? t("employees:reviewer.none")}</Typography.Text>
      <Select
        style={{ minWidth: 260 }}
        placeholder={t("employees:reviewer.assign")}
        value={currentReviewerId ?? undefined}
        options={(usersQuery.data ?? []).map((u) => ({ value: u.id, label: u.staff_no }))}
        onChange={(value: number) => mutation.mutate(value)}
        loading={mutation.isPending}
      />
    </Space>
  );
}

function SalaryTab({ employeeId }: { employeeId: number }) {
  const { t } = useTranslation(["common", "employees", "org"]);
  const queryClient = useQueryClient();
  const canManage = useAuthStore((s) => hasPermission(s.user?.roles ?? [], "MANAGE_EMPLOYEES"));
  const salariesQuery = useQuery({
    queryKey: ["employees", employeeId, "salaries"],
    queryFn: () => listSalaries(employeeId),
  });

  const createMutation = useMutation({
    mutationFn: (payload: { effective_from: string; effective_to?: string; base_salary: string }) =>
      createSalary(employeeId, payload),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ["employees", employeeId, "salaries"] }),
  });

  return (
    <div>
      <Table<EmployeeSalaryOut>
        size="small"
        rowKey="id"
        loading={salariesQuery.isLoading}
        dataSource={salariesQuery.data ?? []}
        pagination={false}
        style={{ marginBottom: 24 }}
        columns={[
          { title: t("org:rates.from"), dataIndex: "effective_from", render: (v: string) => <Ltr>{v}</Ltr> },
          {
            title: t("org:rates.to"),
            dataIndex: "effective_to",
            render: (v: string | null) => <Ltr>{v ?? t("org:rates.openEnded")}</Ltr>,
          },
          {
            title: t("employees:salary.baseSalary"),
            dataIndex: "base_salary",
            render: (v: string) => <Ltr>{v} SAR</Ltr>,
          },
        ]}
      />

      {canManage && (
        <>
          <Typography.Title level={5}>{t("employees:salary.addNew")}</Typography.Title>
          <Form
            layout="inline"
            onFinish={(values: { effective_from: dayjs.Dayjs; effective_to?: dayjs.Dayjs; base_salary: number }) =>
              createMutation.mutate({
                effective_from: values.effective_from.format("YYYY-MM-DD"),
                effective_to: values.effective_to ? values.effective_to.format("YYYY-MM-DD") : undefined,
                base_salary: String(values.base_salary),
              })
            }
          >
            <Form.Item name="effective_from" rules={[{ required: true }]}>
              <DatePicker placeholder={t("org:rates.from")} />
            </Form.Item>
            <Form.Item name="effective_to">
              <DatePicker placeholder={t("org:rates.to")} />
            </Form.Item>
            <Form.Item name="base_salary" rules={[{ required: true }]}>
              <InputNumber min={0} addonAfter="SAR" placeholder={t("employees:salary.baseSalary")} />
            </Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit" loading={createMutation.isPending}>
                {t("common:common.create")}
              </Button>
            </Form.Item>
          </Form>
          {createMutation.isError && (
            <Typography.Text type="danger">{t("employees:salary.overlapError")}</Typography.Text>
          )}
        </>
      )}
    </div>
  );
}

export default EmployeeDetailPage;
