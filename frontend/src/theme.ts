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

export const typography = StyleSheet.create({
  h1: { fontSize: 36, fontWeight: '800', color: colors.textPrimary, letterSpacing: -1 },
  h2: { fontSize: 28, fontWeight: '700', color: colors.textPrimary, letterSpacing: -0.5 },
  h3: { fontSize: 22, fontWeight: '700', color: colors.textPrimary },
  bodyLg: { fontSize: 17, color: colors.textPrimary },
  body: { fontSize: 15, color: colors.textPrimary },
  bodySm: { fontSize: 13, color: colors.textSecondary },
  caption: { fontSize: 11, fontWeight: '600', color: colors.textTertiary, letterSpacing: 1.5, textTransform: 'uppercase' },
});
