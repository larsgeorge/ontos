import i18n from 'i18next';
import type { Resource } from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

// Dynamically import all translation JSON files using Vite's import.meta.glob
// This makes path resolution resilient across environments (e.g., Databricks Apps)
const localeModules = import.meta.glob('./locales/*/*.json', {
  eager: true,
  import: 'default',
}) as Record<string, any>;

// Fallback explicit imports to guarantee inclusion of critical namespaces
// If packaging ever misses a file, these ensure it's still bundled.
import settingsEN from './locales/en/settings.json';
import settingsDE from './locales/de/settings.json';
import settingsJA from './locales/ja/settings.json';

const resources: Resource = {};

for (const [modulePath, moduleExports] of Object.entries(localeModules)) {
  const match = modulePath.match(/\.\/locales\/([^/]+)\/([^/]+)\.json$/);
  if (!match) continue;
  const [, languageCode, namespace] = match;
  if (!resources[languageCode]) resources[languageCode] = {};
  (resources[languageCode] ||= {} as any)[namespace] = moduleExports as any;
}

const namespaces = resources['en'] ? Object.keys(resources['en']) : ['common'];

// Diagnostics to verify loaded languages and namespaces at runtime
try {
  // eslint-disable-next-line no-console
  console.log('[i18n] Discovered locale modules:', Object.keys(localeModules));
  // eslint-disable-next-line no-console
  console.log('[i18n] Loaded languages:', Object.keys(resources));
  // eslint-disable-next-line no-console
  console.log('[i18n] Namespaces for en:', namespaces);
} catch {}

// Ensure 'settings' namespace exists by injecting explicit imports if missing
const fallbackSettingsByLang: Record<string, any> = {
  en: settingsEN,
  de: settingsDE,
  ja: settingsJA,
};

for (const [lang, data] of Object.entries(fallbackSettingsByLang)) {
  if (!resources[lang]) resources[lang] = {};
  if (!(resources[lang] as any)['settings']) {
    (resources[lang] as any)['settings'] = data as any;
  }
}

// Configure i18next
i18n
  .use(LanguageDetector) // Detect user language
  .use(initReactI18next) // Pass i18n instance to react-i18next
  .init({
    resources,
    fallbackLng: 'en', // Fallback language
    defaultNS: 'common', // Default namespace
    ns: namespaces, // Available namespaces discovered from files
    load: 'languageOnly', // Normalize languages like en-US -> en
    supportedLngs: Object.keys(resources),

    interpolation: {
      escapeValue: false, // React already escapes values
    },

    detection: {
      // Order of language detection
      order: ['localStorage', 'navigator'],
      // Cache user language
      caches: ['localStorage'],
      lookupLocalStorage: 'i18nextLng',
    },

    react: {
      useSuspense: false, // Disable suspense for easier integration
    },
  });

export default i18n;
