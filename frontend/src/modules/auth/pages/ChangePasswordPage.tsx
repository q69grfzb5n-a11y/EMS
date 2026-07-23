import { startTransition, useState } from "react";
import { Alert, Button, Card, Form, Input, Typography, message } from "antd";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { changePassword } from "@/modules/auth/api/authApi";
import { useAuthStore } from "@/shared/auth/authStore";
import { LTR_INPUT_STYLES } from "@/shared/ui/ltrInput";
import { extractApiErrorCode } from "@/shared/utils/apiError";

interface ChangePasswordFormValues {
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
}

export function ChangePasswordPage() {
  const { t } = useTranslation(["common", "auth"]);
  const navigate = useNavigate();
  const mustChangePassword = useAuthStore((state) => state.user?.must_change_password ?? false);
  const updateUser = useAuthStore((state) => state.updateUser);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onFinish = async (values: ChangePasswordFormValues) => {
    setError(null);
    setSubmitting(true);
    try {
      await changePassword(values.currentPassword, values.newPassword);
      updateUser({ must_change_password: false });
      void message.success(t("auth:changePassword.success"));
      startTransition(() => {
        navigate("/", { replace: true });
      });
    } catch (err) {
      setError(t(`auth:errors.${extractApiErrorCode(err)}`));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        minHeight: "100vh",
        padding: 16,
        background: "#F5F7F7",
      }}
    >
      <Card style={{ width: "100%", maxWidth: 420 }}>
        <Typography.Title level={3} style={{ textAlign: "center", marginTop: 0 }}>
          {t("auth:changePassword.title")}
        </Typography.Title>
        {mustChangePassword && (
          <Alert
            type="warning"
            message={t("auth:changePassword.forcedNotice")}
            style={{ marginBottom: 16 }}
            showIcon
          />
        )}
        {error && <Alert type="error" message={error} style={{ marginBottom: 16 }} showIcon />}
        <Form layout="vertical" onFinish={onFinish}>
          <Form.Item
            name="currentPassword"
            label={t("auth:changePassword.currentPassword")}
            rules={[{ required: true }]}
          >
            <Input.Password
              autoFocus
              autoComplete="current-password"
              dir="ltr"
              styles={LTR_INPUT_STYLES}
            />
          </Form.Item>
          <Form.Item
            name="newPassword"
            label={t("auth:changePassword.newPassword")}
            validateTrigger="onBlur"
            rules={[
              { required: true },
              { min: 8, message: t("auth:changePassword.passwordTooShort") },
            ]}
          >
            <Input.Password autoComplete="new-password" dir="ltr" styles={LTR_INPUT_STYLES} />
          </Form.Item>
          <Form.Item
            name="confirmPassword"
            label={t("auth:changePassword.confirmPassword")}
            dependencies={["newPassword"]}
            validateTrigger="onBlur"
            rules={[
              { required: true },
              ({ getFieldValue }) => ({
                validator(_, value: string) {
                  if (!value || getFieldValue("newPassword") === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error(t("auth:changePassword.passwordMismatch")));
                },
              }),
            ]}
          >
            <Input.Password autoComplete="new-password" dir="ltr" styles={LTR_INPUT_STYLES} />
          </Form.Item>
          <Form.Item style={{ marginBottom: 0 }}>
            <Button type="primary" htmlType="submit" block loading={submitting}>
              {t("auth:changePassword.submit")}
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}

export default ChangePasswordPage;
