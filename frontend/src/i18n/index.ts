import { createI18n } from 'vue-i18n';
import en from './locales/en';
import de from './locales/de';

export const i18n = createI18n({
  legacy: false,
  locale: localStorage.getItem('hubex_locale') || 'en',
  fallbackLocale: 'en',
  messages: { en, de },
});

export function setLocale(locale: 'en' | 'de') {
  i18n.global.locale.value = locale;
  localStorage.setItem('hubex_locale', locale);
  document.documentElement.setAttribute('lang', locale);
}

export function getCurrentLocale(): string {
  return i18n.global.locale.value;
}
