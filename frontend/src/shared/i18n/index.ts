import i18next from "i18next";
import { initReactI18next } from "react-i18next";
import resourcesToBackend from "i18next-resources-to-backend";

export const SUPPORTED_LANGUAGES = ["ar", "en"] as const;
export type SupportedLanguage = (typeof SUPPORTED_LANGUAGES)[number];

const DEFAULT_LANGUAGE: SupportedLanguage = "ar";

// Every module owns its own locales/<lang>/<namespace>.json — this glob discovers
// them all so useTranslation("<namespace>") works without a central registry to update.
const localeModules = import.meta.glob<{ default: Record<string, unknown> }>([
  "./locales/*/*.json",
  "../../modules/*/locales/*/*.json",
]);

const localeLoaders = new Map<string, () => Promise<{ default: Record<string, unknown> }>>();
for (const [path, loader] of Object.entries(localeModules)) {
  const match = /locales\/([a-z]+)\/([a-zA-Z0-9_-]+)\.json$/.exec(path);
  if (match) {
    const [, language, namespace] = match;
    localeLoaders.set(`${language}/${namespace}`, loader);
  }
}

void i18next
  .use(initReactI18next)
  .use(
    resourcesToBackend((language: string, namespace: string) => {
      const loader = localeLoaders.get(`${language}/${namespace}`);
      return loader ? loader() : Promise.resolve({ default: {} });
    }),
  )
  .init({
    lng: localStorage.getItem("lang") ?? DEFAULT_LANGUAGE,
    fallbackLng: DEFAULT_LANGUAGE,
    ns: ["common"],
    defaultNS: "common",
    interpolation: { escapeValue: false },
    // Namespaces load on demand (see resourcesToBackend above) with no
    // <Suspense> boundary anywhere in the app to catch the resulting
    // suspend — react-i18next's default useSuspense:true throws React error
    // #426 ("suspended while responding to synchronous input") the moment a
    // page needs a namespace that isn't loaded yet outside a startTransition.
    // Disabling it renders with whatever's available and re-renders normally
    // once the namespace resolves, instead of suspending at all.
    react: { useSuspense: false },
  });

export default i18next;
