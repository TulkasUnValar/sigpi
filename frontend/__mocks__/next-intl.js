// Mock for next-intl
// This mock loads real translations from messages files for testing
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load translations based on locale (default to English for tests)
let translationsCache = null;

function loadTranslations(locale = 'es') {
  if (translationsCache) return translationsCache;

  try {
    const messagesPath = path.join(__dirname, '..', 'messages', `${locale}.json`);
    const content = fs.readFileSync(messagesPath, 'utf-8');
    translationsCache = JSON.parse(content);
    return translationsCache;
  } catch (error) {
    console.warn('Could not load translations, using empty object:', error.message);
    return {};
  }
}

// Get a value from nested object using dot notation
function getNestedValue(obj, keyPath) {
  return keyPath.split('.').reduce((current, key) => {
    return current && current[key] !== undefined ? current[key] : undefined;
  }, obj);
}

// Substitute parameters in translation string
function substituteParams(template, params) {
  if (!params || typeof template !== 'string') return template;

  return template.replace(/\{(\w+)\}/g, (match, paramName) => {
    return params[paramName] !== undefined ? String(params[paramName]) : match;
  });
}

module.exports = {
  useTranslations: (namespace) => {
    const translations = loadTranslations('es');

    return (key, params) => {
      // Build full key path
      const fullPath = namespace ? `${namespace}.${key}` : key;

      // Try to find the translation
      const value = getNestedValue(translations, fullPath);

      if (value !== undefined) {
        return substituteParams(value, params);
      }

      // If not found, return just the key (without namespace) for better test compatibility
      console.warn(`Translation not found: ${fullPath}`);
      return key;
    };
  },

  useLocale: () => "es",

  useMessages: () => loadTranslations('es'),

  useNow: () => new Date(),

  useTimeZone: () => "UTC",

  useFormatter: () => {
    return {
      dateTime: (date) => date.toLocaleString(),
      number: (num) => num.toString(),
    };
  },

  NextIntlClientProvider: ({ children }) => children,

  createTranslator: ({ messages, locale }) => {
    const translations = messages || loadTranslations(locale || 'es');

    return (key, params) => {
      const value = getNestedValue(translations, key);

      if (value !== undefined) {
        return substituteParams(value, params);
      }

      return key;
    };
  },
};
