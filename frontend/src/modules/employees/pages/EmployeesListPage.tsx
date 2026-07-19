import { useState } from "react";
import { Button, Form, Input, Modal, Select, Space, Tag, Typography } from "antd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { createEmployee, listEmployees } from "@/modules/employees/api/employeesApi";
import type { EmployeeOut } from "@/modules/employees/types";
import { listDepartments, listPositions } from "@/modules/org/api/orgApi";
import { Can } from "@/shared/auth/Can";
import { useLocalizedField } from "@/shared/hooks/useLocalizedField";
import { DataTable } from "@/shared/ui/DataTable";
import { Ltr } from "@/shared/ui/Ltr";
import { LTR_INPUT_STYLES } from "@/shared/ui/ltrInput";

export function EmployeesListPage() {
  const { t } = useTranslation(["common", "employees"]);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const localized = useLocalizedField();
  const employeesQuery = useQuery({ queryKey: ["employees"], queryFn: listEmployees });
  const departmentsQuery = useQuery({ queryKey: ["org", "departments"], queryFn: listDepartments });
  const positionsQuery = useQuery({ queryKey: ["org", "positions"], queryFn: listPositions });
  const [createOpen, setCreateOpen] = useState(false);

  const createMutation = useMutation({
    mutationFn: createEmployee,
    onSuccess: () => {
      setCreateOpen(false);
      void queryClient.invalidateQueries({ queryKey: ["employees"] });
    },
  });

  return (
    <div>
      <Space style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <Typography.Title level={3} style={{ margin: 0 }}>
          {t("employees:title")}
        </Typography.Title>
        <Can permission="MANAGE_EMPLOYEES">
          <Button type="primary" onClick={() => setCreateOpen(true)}>
            {t("employees:create")}
          </Button>
        </Can>
      </Space>

      <DataTable<EmployeeOut>
        rowKey="id"
        loading={employeesQuery.isLoading}
        dataSource={employeesQuery.data ?? []}
        searchableText={(e) => [e.staff_no, e.full_name_ar, e.full_name_en ?? ""]}
        onRow={(record) => ({
          onClick: () => navigate(`/employees/${record.id}`),
          style: { cursor: "pointer" },
        })}
        columns={[
          { title: t("employees:staffNo"), dataIndex: "staff_no", render: (v: string) => <Ltr>{v}</Ltr> },
          {
            title: t("employees:name"),
            key: "name",
            render: (_: unknown, e: EmployeeOut) => <bdi>{localized(e.full_name_en, e.full_name_ar)}</bdi>,
          },
          {
            title: t("employees:department"),
            key: "department",
            render: (_: unknown, e: EmployeeOut) => (
              <bdi>{localized(e.department.name_en, e.department.name_ar)}</bdi>
            ),
          },
          {
            title: t("employees:position"),
            key: "position",
            render: (_: unknown, e: EmployeeOut) => (
              <bdi>{localized(e.position.title_en, e.position.title_ar)}</bdi>
            ),
          },
          {
            title: t("employees:status"),
            dataIndex: "employment_status",
            render: (status: string) => (
              <Tag color={status === "active" ? "green" : "default"}>
                {t(`employees:statusValues.${status}`)}
              </Tag>
            ),
          },
        ]}
      />

      <Modal
        title={t("employees:create")}
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        footer={null}
        destroyOnHidden
      >
        <Form
          layout="vertical"
          onFinish={(values: {
            staff_no: string;
            full_name_ar: string;
            full_name_en?: string;
            department_id: number;
            position_id: number;
          }) => createMutation.mutate(values)}
        >
          <Form.Item name="staff_no" label={t("employees:staffNo")} rules={[{ required: true }]}>
            <Input dir="ltr" styles={LTR_INPUT_STYLES} />
          </Form.Item>
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
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={createMutation.isPending} block>
              {t("common:common.create")}
            </Button>
          </Form.Item>
          {createMutation.isError && (
            <Typography.Text type="danger">{t("employees:errors.staffNoTaken")}</Typography.Text>
          )}
        </Form>
      </Modal>
    </div>
  );
}

export default EmployeesListPage;
