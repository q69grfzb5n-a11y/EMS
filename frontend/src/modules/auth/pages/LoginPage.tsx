import { useState } from "react";
import { Alert, Button, Card, Form, Input, Typography } from "antd";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { isAxiosError } from "axios";

import { fetchMe, login as loginRequest } from "@/modules/auth/api/authApi";
import { useAuthStore } from "@/shared/auth/authStore";
import { LTR_INPUT_STYLES } from "@/shared/ui/ltrInput";

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
      navigate(me.must_change_password ? "/change-password" : "/", { replace: true });
    } catch (err) {
      const code = isAxiosError(err) ? err.response?.data?.error?.code : undefined;
      setError(code ? t(`auth:errors.${code}`) : t("auth:errors.invalid_credentials"));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ display: "flex", justifyContent: "center", paddingTop: 80 }}>
      <Card style={{ width: 360 }}>
        <Typography.Title level={3} style={{ textAlign: "center" }}>
          {t("app.name")}
        </Typography.Title>
        {error && <Alert type="error" message={error} style={{ marginBottom: 16 }} showIcon />}
        <Form layout="vertical" onFinish={onFinish}>
          <Form.Item name="staffNo" label={t("auth.staffNo")} rules={[{ required: true }]}>
            <Input autoFocus dir="ltr" styles={LTR_INPUT_STYLES} />
          </Form.Item>
          <Form.Item name="password" label={t("auth.password")} rules={[{ required: true }]}>
            <Input.Password dir="ltr" styles={LTR_INPUT_STYLES} />
          </Form.Item>
          <Form.Item>
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
