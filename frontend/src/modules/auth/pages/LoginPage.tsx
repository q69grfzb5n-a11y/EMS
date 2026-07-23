import { startTransition, useState } from "react";
import { Alert, Button, Card, Form, Input, Typography } from "antd";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { BrandMark } from "@/app/layout/BrandMark";
import { fetchMe, login as loginRequest } from "@/modules/auth/api/authApi";
import { useAuthStore } from "@/shared/auth/authStore";
import { LTR_INPUT_STYLES } from "@/shared/ui/ltrInput";
import { extractApiErrorCode } from "@/shared/utils/apiError";

interface LoginFormValues {
  staffNo: string;
  password: string;
}

export function LoginPage() {
  const { t } = useTranslation(["common", "auth"]);
  const navigate = useNavigate();
  const setSession = useAuthStore((state) => state.setSession);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onFinish = async (values: LoginFormValues) => {
    setError(null);
    setSubmitting(true);
    try {
      const token = await loginRequest(values.staffNo, values.password);
      useAuthStore.getState().setAccessToken(token.access_token);
      const me = await fetchMe();
      setSession(token.access_token, me);
      startTransition(() => {
        navigate(me.must_change_password ? "/change-password" : "/", { replace: true });
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
      <Card style={{ width: "100%", maxWidth: 380 }}>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
          <BrandMark size={48} />
          <div style={{ textAlign: "center" }}>
            <Typography.Title level={3} style={{ margin: 0 }}>
              {t("app.orgShort")}
            </Typography.Title>
            <Typography.Text type="secondary">{t("app.name")}</Typography.Text>
          </div>
        </div>
        {error && (
          <Alert type="error" message={error} style={{ marginTop: 24 }} showIcon closable />
        )}
        <Form layout="vertical" onFinish={onFinish} style={{ marginTop: 24 }}>
          <Form.Item name="staffNo" label={t("auth.staffNo")} rules={[{ required: true }]}>
            <Input autoFocus autoComplete="username" dir="ltr" styles={LTR_INPUT_STYLES} />
          </Form.Item>
          <Form.Item name="password" label={t("auth.password")} rules={[{ required: true }]}>
            <Input.Password
              autoComplete="current-password"
              dir="ltr"
              styles={LTR_INPUT_STYLES}
            />
          </Form.Item>
          <Form.Item style={{ marginBottom: 0 }}>
            <Button type="primary" htmlType="submit" block loading={submitting}>
              {t("auth.login")}
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}

export default LoginPage;
