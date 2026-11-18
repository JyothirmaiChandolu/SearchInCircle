// Bento grid + Aurora palette, per the SearchInCircle prototype's design system.
export const AURORA = {
  bg: '#EDEFF9',
  surface2: '#F4F6FC',
  ink: '#232A4A',
  ink2: '#505C86',
  ink3: '#5A6690',
  line: '#DADFF0',
  primary: '#4F5BD5',
  avBg: '#E4E6FA',
  avFg: '#3B459F',
  hue3: '#67BDE8',
  hue4: '#A78BFA',
  danger: '#B3261E',
} as const;

// CIRCA palette — Trusted Circle Matching App prototype. Used by the auth flow (login/OTP) only.
export const CIRCA = {
  ink: '#17172B',
  muted: '#6B6B82',
  soft: '#F7F6FC',
  line: '#E7E4F0',
  paper: '#FFFFFF',
  brand: '#4F46E5',
  brandDark: '#3730A3',
  brandSoft: '#EEEDFF',
  accent: '#8B5CF6',
  success: '#2563EB',
  danger: '#B3261E',
  heroGradient: ['#24205D', '#4338CA', '#7C3AED'] as const,
  buttonGradient: ['#4338CA', '#6366F1', '#7C3AED'] as const,
  heroBlur: 'rgba(196,181,253,0.28)',
  dot: '#C4B5FD',
} as const;
