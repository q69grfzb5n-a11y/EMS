import { useTranslation } from "react-i18next";

/**
 * Business data (department/position names, etc.) comes from the API as *_en/*_ar
 * pairs, distinct from UI chrome strings which flow through i18next. This picks the
 * field matching the active language, falling back to Arabic (source of truth —
 * every row has it) when the English pair is missing, e.g. an unenriched employee.
 */
export function useLocalizedField(): (en: string | null | undefined, ar: string) => string {
  const { i18n } = useTranslation();
  return (en, ar) => (i18n.language.startsWith("en") ? (en ?? ar) : ar);
}
