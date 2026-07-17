import { useEffect, type PropsWithChildren } from "react";
import { useTranslation } from "react-i18next";
import { ConfigProvider } from "antd";
import enUS from "antd/locale/en_US";
import arEG from "antd/locale/ar_EG";
import dayjs from "dayjs";
import "dayjs/locale/ar";
import "dayjs/locale/en";

import type { SupportedLanguage } from "@/shared/i18n";

const DIRECTIONS: Record<SupportedLanguage, "rtl" | "ltr"> = {
  ar: "rtl",
  en: "ltr",
};

const ANTD_LOCALES = {
  ar: arEG,
  en: enUS,
};

export function LocaleProvider({ children }: PropsWithChildren) {
  const { i18n } = useTranslation();
  const language = (i18n.resolvedLanguage ?? "ar") as SupportedLanguage;

  useEffect(() => {
    const applyLanguage = (lng: string) => {
      const resolved = (lng in DIRECTIONS ? lng : "ar") as SupportedLanguage;
      document.documentElement.lang = resolved;
      document.documentElement.dir = DIRECTIONS[resolved];
      dayjs.locale(resolved);
      localStorage.setItem("lang", resolved);
    };

    applyLanguage(language);
    i18n.on("languageChanged", applyLanguage);
    return () => {
      i18n.off("languageChanged", applyLanguage);
    };
  }, [i18n, language]);

  return (
    <ConfigProvider direction={DIRECTIONS[language]} locale={ANTD_LOCALES[language]}>
      {children}
    </ConfigProvider>
  );
}
