import { Button } from "antd";
import { useTranslation } from "react-i18next";

import type { SupportedLanguage } from "@/shared/i18n";

export function LanguageSwitcher() {
  const { t, i18n } = useTranslation();
  const current = (i18n.resolvedLanguage ?? "ar") as SupportedLanguage;

  const toggle = () => {
    void i18n.changeLanguage(current === "ar" ? "en" : "ar");
  };

  return (
    <Button type="text" onClick={toggle}>
      {t("language.switchTo")}
    </Button>
  );
}
