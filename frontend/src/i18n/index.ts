import { createI18n } from 'vue-i18n';
import en from './locales/en';
import de from './locales/de';
import fr from './locales/fr';
import es from './locales/es';
import it from './locales/it';
import nl from './locales/nl';
import pl from './locales/pl';
import pt from './locales/pt';

export type SupportedLocale = 'en' | 'de' | 'fr' | 'es' | 'it' | 'nl' | 'pl' | 'pt';

export const i18n = createI18n({
  legacy: false,
  locale: localStorage.getItem('hubex_locale') || 'en',
  fallbackLocale: 'en',
  messages: { en, de, fr, es, it, nl, pl, pt },
});

export function setLocale(locale: SupportedLocale) {
  i18n.global.locale.value = locale;
  localStorage.setItem('hubex_locale', locale);
  document.documentElement.setAttribute('lang', locale);
}

export function getCurrentLocale(): string {
  return i18n.global.locale.value;
}
