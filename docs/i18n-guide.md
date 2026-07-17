# i18n Guide

## Defaults

Default locale is **Arabic**, developed RTL-first. Language stored in `localStorage.lang`; `index.html` sets `<html lang dir>` before the bundle loads to avoid an RTL flash.

## Rules

- Logical CSS properties only (`margin-inline-start`, not `margin-left`) — stylelint-enforced once stylelint is added.
- Mixed Arabic/Latin text wrapped in `<bdi>`.
- Numbers/IDs/money rendered in LTR-isolated spans with tabular-nums; **Western digits** (`ar-SA-u-nu-latn`), never Eastern Arabic numerals.
- UI chrome text comes from i18next namespaces (`src/shared/i18n/locales/{en,ar}/*.json`, one namespace per module, lazy-loaded per route). Business data comes from the API's `*_en`/`*_ar` field pairs via `useLocalizedField` (added Phase 2).
- CI enforces en/ar key-parity across all namespaces (added once more than the `common` namespace exists).

## RTL choke point

`frontend/src/app/providers/LocaleProvider.tsx` — on `languageChanged`, sets `document.documentElement.dir/lang`, antd `ConfigProvider direction+locale`, and `dayjs.locale()`. All RTL-sensitive logic should live here, not scattered across components.

## Adding a new namespace

1. Add `locales/en/<module>.json` and `locales/ar/<module>.json` under the module folder.
2. Import lazily where the route/module loads (see `i18next-resources-to-backend` wiring in `src/shared/i18n/index.ts`).
3. Keep keys identical across both locale files — CI will fail on drift once the parity test is added.
