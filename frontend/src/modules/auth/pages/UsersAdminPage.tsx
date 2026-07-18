import { useState } from "react";
import {
  Button,
  Checkbox,
  Form,
  Input,
  Modal,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import {
  assignRoles,
  createUser,
  listRoles,
  listUsers,
  patchUser,
  resetPassword,
} from "@/modules/auth/api/authApi";
import type { RoleOut, UserOut } from "@/modules/auth/types";
import { Can } from "@/shared/auth/Can";
import { useAuthStore } from "@/shared/auth/authStore";
import { hasPermission } from "@/shared/auth/permissions";

export function UsersAdminPage() {
  const { t } = useTranslation(["common", "auth"]);
  const queryClient = useQueryClient();
  const isHR = useAuthStore((state) => hasPermission(state.user?.roles ?? [], "MANAGE_ROLES"));

  const usersQuery = useQuery({ queryKey: ["users"], queryFn: listUsers });
  const rolesQuery = useQuery({ queryKey: ["roles"], queryFn: listRoles });

  const [createOpen, setCreateOpen] = useState(false);
  const [rolesModalUser, setRolesModalUser] = useState<UserOut | null>(null);
  const [resetModalUser, setResetModalUser] = useState<UserOut | null>(null);

  const invalidateUsers = () => queryClient.invalidateQueries({ queryKey: ["users"] });

  const createMutation = useMutation({
    mutationFn: ({ staffNo, password }: { staffNo: string; password: string }) =>
      createUser(staffNo, password),
    onSuccess: () => {
      void message.success(t("auth:users.create"));
      setCreateOpen(false);
      void invalidateUsers();
    },
  });

  const toggleActiveMutation = useMutation({
    mutationFn: (user: UserOut) => patchUser(user.id, !user.is_active),
    onSuccess: () => void invalidateUsers(),
  });

  const assignRolesMutation = useMutation({
    mutationFn: ({ userId, roleCodes }: { userId: number; roleCodes: string[] }) =>
      assignRoles(userId, roleCodes),
    onSuccess: () => {
      setRolesModalUser(null);
      void invalidateUsers();
    },
  });

  const resetPasswordMutation = useMutation({
    mutationFn: ({ userId, newPassword }: { userId: number; newPassword: string }) =>
      resetPassword(userId, newPassword),
    onSuccess: () => {
      void message.success(t("auth:users.resetPassword"));
      setResetModalUser(null);
      void invalidateUsers();
    },
  });

  const columns = [
    { title: t("auth:users.staffNo"), dataIndex: "staff_no" },
    {
      title: t("auth:users.roles"),
      dataIndex: "roles",
      render: (roles: string[]) => (
        <Space wrap>
          {roles.map((role) => (
            <Tag key={role}>{role}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: t("auth:users.status"),
      dataIndex: "is_active",
      render: (isActive: boolean) => (
        <Tag color={isActive ? "green" : "default"}>
          {isActive ? t("auth:users.active") : t("auth:users.inactive")}
        </Tag>
      ),
    },
    {
      title: t("auth:users.actions"),
      key: "actions",
      render: (_: unknown, user: UserOut) => (
        <Space>
          <Can permission="MANAGE_ROLES">
            <Button size="small" onClick={() => setRolesModalUser(user)}>
              {t("auth:users.assignRoles")}
            </Button>
            <Button size="small" onClick={() => setResetModalUser(user)}>
              {t("auth:users.resetPassword")}
            </Button>
          </Can>
          <Button size="small" onClick={() => toggleActiveMutation.mutate(user)}>
            {user.is_active ? t("auth:users.deactivate") : t("auth:users.activate")}
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Space
        style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}
      >
        <Typography.Title level={3} style={{ margin: 0 }}>
          {t("auth:users.title")}
        </Typography.Title>
        <Button type="primary" onClick={() => setCreateOpen(true)}>
          {t("auth:users.createUser")}
        </Button>
      </Space>

      <Table
        rowKey="id"
        loading={usersQuery.isLoading}
        dataSource={usersQuery.data ?? []}
        columns={columns}
        pagination={false}
      />

      <Modal
        title={t("auth:users.createUser")}
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        footer={null}
        destroyOnHidden
      >
        <Form
          layout="vertical"
          onFinish={(values: { staffNo: string; password: string }) =>
            createMutation.mutate(values)
          }
        >
          <Form.Item name="staffNo" label={t("auth:users.staffNo")} rules={[{ required: true }]}>
            <Input dir="ltr" />
          </Form.Item>
          <Form.Item
            name="password"
            label={t("auth:users.password")}
            rules={[{ required: true, min: 8 }]}
          >
            <Input.Password dir="ltr" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={createMutation.isPending} block>
              {t("auth:users.create")}
            </Button>
          </Form.Item>
        </Form>
      </Modal>

      {rolesModalUser && (
        <AssignRolesModal
          user={rolesModalUser}
          roles={rolesQuery.data ?? []}
          onCancel={() => setRolesModalUser(null)}
          onSubmit={(roleCodes) =>
            assignRolesMutation.mutate({ userId: rolesModalUser.id, roleCodes })
          }
          submitting={assignRolesMutation.isPending}
        />
      )}

      {resetModalUser && (
        <Modal
          title={t("auth:users.resetPassword")}
          open
          onCancel={() => setResetModalUser(null)}
          footer={null}
          destroyOnHidden
        >
          <Form
            layout="vertical"
            onFinish={(values: { newPassword: string }) =>
              resetPasswordMutation.mutate({
                userId: resetModalUser.id,
                newPassword: values.newPassword,
              })
            }
          >
            <Form.Item
              name="newPassword"
              label={t("auth:users.newPassword")}
              rules={[{ required: true, min: 8 }]}
            >
              <Input.Password autoFocus dir="ltr" />
            </Form.Item>
            <Form.Item>
              <Button
                type="primary"
                htmlType="submit"
                loading={resetPasswordMutation.isPending}
                block
              >
                {t("auth:users.save")}
              </Button>
            </Form.Item>
          </Form>
        </Modal>
      )}

      {!isHR && null}
    </div>
  );
}

interface AssignRolesModalProps {
  user: UserOut;
  roles: RoleOut[];
  onCancel: () => void;
  onSubmit: (roleCodes: string[]) => void;
  submitting: boolean;
}

function AssignRolesModal({
  user,
  roles,
  onCancel,
  onSubmit,
  submitting,
}: AssignRolesModalProps) {
  const { t } = useTranslation("auth");
  const [selected, setSelected] = useState<string[]>(user.roles);

  return (
    <Modal
      title={`${t("users.assignRoles")} — ${user.staff_no}`}
      open
      onCancel={onCancel}
      onOk={() => onSubmit(selected)}
      confirmLoading={submitting}
    >
      <Checkbox.Group
        style={{ display: "flex", flexDirection: "column", gap: 8 }}
        value={selected}
        onChange={(values) => setSelected(values as string[])}
      >
        {roles.map((role) => (
          <Checkbox key={role.code} value={role.code}>
            {role.name_en} / {role.name_ar}
          </Checkbox>
        ))}
      </Checkbox.Group>
    </Modal>
  );
}

export default UsersAdminPage;
