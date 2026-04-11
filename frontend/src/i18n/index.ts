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

const _initialLocale = (localStorage.getItem('hubex_locale') || 'en') as SupportedLocale;

export const i18n = createI18n({
  legacy: false,
  locale: _initialLocale,
  fallbackLocale: 'en',
  messages: { en, de, fr, es, it, nl, pl, pt },
});

// Sprint 8 R4 A11y-F02: sync <html lang> with the saved locale at bootstrap
// so screen readers & the browser receive the correct language on page load.
// Without this, html[lang] was stuck at "en" (from index.html) even when
// the user's saved locale was "de", which hurts accessibility and SEO.
if (typeof document !== 'undefined') {
  document.documentElement.setAttribute('lang', _initialLocale);
}

export function setLocale(locale: SupportedLocale) {
  i18n.global.locale.value = locale;
  localStorage.setItem('hubex_locale', locale);
  document.documentElement.setAttribute('lang', locale);
}

export function getCurrentLocale(): string {
  return i18n.global.locale.value;
}
