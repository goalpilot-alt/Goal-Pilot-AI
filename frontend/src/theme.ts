import { StyleSheet } from 'react-native';

export const colors = {
  bg: '#09090B',
  surface: '#18181B',
  surfaceElev: '#27272A',
  border: 'rgba(255,255,255,0.08)',
  primary: '#FF5E00',
  primaryGlow: 'rgba(255, 94, 0, 0.4)',
  secondary: '#00F0FF',
  textPrimary: '#FAFAFA',
  textSecondary: '#A1A1AA',
  textTertiary: '#71717A',
  success: '#10B981',
  error: '#EF4444',
  warning: '#F59E0B',
};

export const spacing = { xs: 4, sm: 8, md: 16, lg: 24, xl: 32, xxl: 48 };
export const radii = { sm: 8, md: 16, lg: 24, full: 9999 };

// boxShadow strings (Expo SDK 53+ replaces deprecated shadow* props)
// Format: "<x> <y> <blur> <spread?> <color>"
export const shadows = {
  primarySm:    `0px 2px 8px rgba(255, 94, 0, 0.4)`,
  primaryMd:    `0px 4px 14px rgba(255, 94, 0, 0.5)`,
  primaryLg:    `0px 6px 16px rgba(255, 94, 0, 0.5)`,
  primaryGlow:  `0px 0px 8px rgba(255, 94, 0, 0.8)`,
  primarySoft:  `0px 4px 20px rgba(255, 94, 0, 0.3)`,
  cardElev:     `0px 4px 12px rgba(0, 0, 0, 0.25)`,
};

export const typography = StyleSheet.create({
  h1: { fontSize: 36, fontWeight: '800', color: colors.textPrimary, letterSpacing: -1 },
  h2: { fontSize: 28, fontWeight: '700', color: colors.textPrimary, letterSpacing: -0.5 },
  h3: { fontSize: 22, fontWeight: '700', color: colors.textPrimary },
  bodyLg: { fontSize: 17, color: colors.textPrimary },
  body: { fontSize: 15, color: colors.textPrimary },
  bodySm: { fontSize: 13, color: colors.textSecondary },
  caption: { fontSize: 11, fontWeight: '600', color: colors.textTertiary, letterSpacing: 1.5, textTransform: 'uppercase' },
});
