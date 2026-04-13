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

// Priority: localStorage (user already changed) > browser language > fallback "de"
function _detectLocale(): SupportedLocale {
  const saved = localStorage.getItem('hubex_locale');
  if (saved && ['en', 'de', 'fr', 'es', 'it', 'nl', 'pl', 'pt'].includes(saved)) {
    return saved as SupportedLocale;
  }
  // Browser language detection
  const browserLang = navigator.language?.split('-')[0] || '';
  if (['en', 'de', 'fr', 'es', 'it', 'nl', 'pl', 'pt'].includes(browserLang)) {
    return browserLang as SupportedLocale;
  }
  return 'de'; // Default for German test users
}
const _initialLocale = _detectLocale();

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

/**
 * Sync locale from user preferences (called after login/app init).
 * If the user has a saved locale preference in the backend, use it.
 */
export async function syncLocaleFromUser(): Promise<void> {
  try {
    // Only sync if user hasn't already set a locale in this browser
    if (localStorage.getItem('hubex_locale')) return;

    const { apiFetch, hasToken } = await import('../lib/api');
    if (!hasToken()) return;

    const me = await apiFetch<{ preferences?: { locale?: string } }>('/api/v1/users/me');
    const userLocale = me.preferences?.locale;
    if (userLocale && ['en', 'de', 'fr', 'es', 'it', 'nl', 'pl', 'pt'].includes(userLocale)) {
      setLocale(userLocale as SupportedLocale);
    }
  } catch {
    // ignore — user preference sync is best-effort
  }
}
