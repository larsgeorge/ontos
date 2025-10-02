import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

// Import translation files
import commonEN from './locales/en/common.json';
import navigationEN from './locales/en/navigation.json';
import settingsEN from './locales/en/settings.json';
import featuresEN from './locales/en/features.json';

import commonDE from './locales/de/common.json';
import navigationDE from './locales/de/navigation.json';
import settingsDE from './locales/de/settings.json';
import featuresDE from './locales/de/features.json';

// Configure i18next
i18n
  .use(LanguageDetector) // Detect user language
  .use(initReactI18next) // Pass i18n instance to react-i18next
  .init({
    resources: {
      en: {
        common: commonEN,
        navigation: navigationEN,
        settings: settingsEN,
        features: featuresEN,
      },
      de: {
        common: commonDE,
        navigation: navigationDE,
        settings: settingsDE,
        features: featuresDE,
      },
    },
    fallbackLng: 'en', // Fallback language
    defaultNS: 'common', // Default namespace
    ns: ['common', 'navigation', 'settings', 'features'], // Available namespaces

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
