import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

// EU Languages
import enTranslations from './locales/en.json';
import nlTranslations from './locales/nl.json';
import deTranslations from './locales/de.json';
import frTranslations from './locales/fr.json';
import esTranslations from './locales/es.json';
import plTranslations from './locales/pl.json';

// Non-EU Languages (commonly spoken by expats in NL)
import ruTranslations from './locales/ru.json';
import ukTranslations from './locales/uk.json';
import trTranslations from './locales/tr.json';
import arTranslations from './locales/ar.json';

i18n
  .use(LanguageDetector) // Detect user language
  .use(initReactI18next) // Pass i18n to react-i18next
  .init({
    resources: {
      // Western European Languages
      en: { translation: enTranslations },
      nl: { translation: nlTranslations },
      de: { translation: deTranslations },
      fr: { translation: frTranslations },
      es: { translation: esTranslations },

      // Eastern European Languages
      pl: { translation: plTranslations },
      ru: { translation: ruTranslations },
      uk: { translation: ukTranslations },

      // Other Languages
      tr: { translation: trTranslations },
      ar: { translation: arTranslations }
    },
    fallbackLng: 'en',
    lng: 'en', // Default language
    interpolation: {
      escapeValue: false // React already escapes
    },
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage']
    }
  });

export default i18n;
