export const branding = {
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
} as const;

export type Branding = typeof branding;
