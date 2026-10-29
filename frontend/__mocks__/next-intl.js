// Mock for next-intl
// This mock provides realistic translations for testing

const translations = {
  common: {
    loading: "Loading…",
    error: "Error",
    save: "Save",
    cancel: "Cancel",
    delete: "Delete",
    edit: "Edit",
    create: "Create",
    search: "Search",
    filter: "Filter",
    actions: "Actions",
  },
  login: {
    loading: "Loading…",
    title: "Sign in to SIGPI",
    ssoSection: "Single Sign-On",
    localSection: "Local Login",
    emailRequired: "Email is required.",
    passwordRequired: "Password is required.",
    loginFailed: "Login failed.",
    emailLabel: "Email",
    emailPlaceholder: "user@example.com",
    passwordLabel: "Password",
    passwordPlaceholder: "••••••••",
    signingIn: "Signing in…",
    signIn: "Sign in",
    signInWithSSO: "Sign in with SSO",
  },
  budgets: {
    title: "Budgets",
    createNew: "Create new budget",
    // Add more as needed
  },
  projects: {
    title: "Projects",
    createNew: "Create new project",
    // Add more as needed
  },
};

module.exports = {
  useTranslations: (namespace) => {
    return (key, params) => {
      const keys = key.split(".");
      let value = translations;
      
      // Try to find the translation in the namespace
      if (namespace && translations[namespace]) {
        value = translations[namespace];
      }
      
      // Navigate through nested keys
      for (const k of keys) {
        if (value && typeof value === "object" && k in value) {
          value = value[k];
        } else {
          // If not found, return the full key
          return namespace ? `${namespace}.${key}` : key;
        }
      }
      
      // Handle parameter substitution
      if (params && typeof value === "string") {
        return value.replace(/\{(\w+)\}/g, (match, paramName) => {
          return params[paramName] !== undefined ? String(params[paramName]) : match;
        });
      }
      
      return typeof value === "string" ? value : (namespace ? `${namespace}.${key}` : key);
    };
  },

  useLocale: () => "en",

  useMessages: () => translations,

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
    return (key, params) => {
      if (params) {
        return `${key}:${JSON.stringify(params)}`;
      }
      return key;
    };
  },
};
