import { reactive } from "vue";
import { apiFetch } from "./api";

const defaults = {
  productName: 'HubEx',
  tagline: 'Universal IoT Device Hub',
  primaryColor: '#F5A623',
  accentColor: '#2DD4BF',
  bgColor: '#111110',
  logoSVG: `<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M16 2L28.66 9V23L16 30L3.34 23V9L16 2Z" stroke="currentColor" stroke-width="1.5" fill="none"/>
    <path d="M16 8L22.93 12V20L16 24L9.07 20V12L16 8Z" fill="currentColor" opacity="0.15"/>
    <circle cx="16" cy="16" r="3" fill="currentColor"/>
    <line x1="16" y1="13" x2="16" y2="8" stroke="currentColor" stroke-width="1.5"/>
    <line x1="18.6" y1="14.5" x2="22.5" y2="12" stroke="currentColor" stroke-width="1.5"/>
    <line x1="18.6" y1="17.5" x2="22.5" y2="20" stroke="currentColor" stroke-width="1.5"/>
    <line x1="16" y1="19" x2="16" y2="24" stroke="currentColor" stroke-width="1.5"/>
    <line x1="13.4" y1="17.5" x2="9.5" y2="20" stroke="currentColor" stroke-width="1.5"/>
    <line x1="13.4" y1="14.5" x2="9.5" y2="12" stroke="currentColor" stroke-width="1.5"/>
  </svg>`,
  logoUrl: null as string | null,
  faviconUrl: null as string | null,
};

export const branding = reactive({ ...defaults });

export type Branding = typeof branding;

/**
 * Apply org branding overrides at runtime.
 * Called after login when org branding is available.
 */
export function applyBranding(config: {
  product_name?: string | null;
  logo_url?: string | null;
  primary_color?: string | null;
  accent_color?: string | null;
  favicon_url?: string | null;
}) {
  if (config.product_name) {
    branding.productName = config.product_name;
    document.title = `${config.product_name} — Mission Control`;
  }
  if (config.logo_url) {
    branding.logoUrl = config.logo_url;
  }
  if (config.primary_color) {
    branding.primaryColor = config.primary_color;
    document.documentElement.style.setProperty('--primary', config.primary_color);
    // Derive hover variant (10% darker)
    document.documentElement.style.setProperty('--primary-hover', config.primary_color);
  }
  if (config.accent_color) {
    branding.accentColor = config.accent_color;
    document.documentElement.style.setProperty('--accent', config.accent_color);
  }
  if (config.favicon_url) {
    branding.faviconUrl = config.favicon_url;
    const link = document.querySelector('link[rel="icon"]') as HTMLLinkElement;
    if (link) link.href = config.favicon_url;
  }
}

/**
 * Load org branding from the API and apply it.
 * Called after login or on app mount when a token exists.
 */
export async function loadOrgBranding(orgId: number): Promise<void> {
  try {
    const data = await apiFetch<{
      product_name: string | null;
      logo_url: string | null;
      primary_color: string | null;
      accent_color: string | null;
      favicon_url: string | null;
    }>(`/api/v1/orgs/${orgId}/branding`);
    applyBranding(data);
  } catch {
    // Ignore — use defaults if branding endpoint fails
  }
}

/**
 * Reset branding to defaults.
 */
export function resetBranding() {
  Object.assign(branding, { ...defaults });
  document.title = `${defaults.productName} — Mission Control`;
  document.documentElement.style.removeProperty('--primary');
  document.documentElement.style.removeProperty('--primary-hover');
  document.documentElement.style.removeProperty('--accent');
}
