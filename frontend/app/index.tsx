import { View, Text, StyleSheet, TouchableOpacity, ImageBackground } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';
import { Feather } from '@expo/vector-icons';
import { colors, spacing, radii, shadows } from '../src/theme';
import { useI18n } from '../src/i18n/I18nProvider';

export default function Welcome() {
  const router = useRouter();
  const { t } = useI18n();

  return (
    <View style={styles.root}>
      <ImageBackground
        source={{ uri: 'https://images.unsplash.com/photo-1767161642116-a3cb82c1a4ce?crop=entropy&cs=srgb&fm=jpg&q=85&w=1200' }}
        style={styles.bg}
        resizeMode="cover"
      >
        <LinearGradient
          colors={['transparent', 'rgba(9,9,11,0.85)', colors.bg]}
          style={StyleSheet.absoluteFill}
          locations={[0, 0.55, 1]}
        />
        <SafeAreaView style={styles.safe} edges={['top', 'bottom']}>
          <View style={styles.top}>
            <View style={styles.logoRow}>
              <View style={styles.logoDot} />
              <Text style={styles.logoText}>GoalPilot AI</Text>
            </View>
          </View>

          <View style={styles.bottom}>
            <Text style={styles.eyebrow} testID="welcome-eyebrow">{t('welcome_eyebrow')}</Text>
            <Text style={styles.title}>{t('welcome_title')}</Text>
            <Text style={styles.subtitle}>{t('welcome_subtitle')}</Text>

            <TouchableOpacity
              testID="welcome-get-started-btn"
              style={styles.primaryBtn}
              activeOpacity={0.85}
              onPress={() => router.push('/register')}
            >
              <Text style={styles.primaryBtnText}>{t('get_started')}</Text>
              <Feather name="arrow-right" size={20} color="#fff" />
            </TouchableOpacity>

            <TouchableOpacity
              testID="welcome-login-btn"
              style={styles.secondaryBtn}
              activeOpacity={0.8}
              onPress={() => router.push('/login')}
            >
              <Text style={styles.secondaryBtnText}>{t('have_account')}</Text>
            </TouchableOpacity>
          </View>
        </SafeAreaView>
      </ImageBackground>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  bg: { flex: 1 },
  safe: { flex: 1, justifyContent: 'space-between', paddingHorizontal: spacing.lg },
  top: { paddingTop: spacing.md },
  logoRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  logoDot: { width: 12, height: 12, borderRadius: 6, backgroundColor: colors.primary, boxShadow: shadows.primaryGlow },
  logoText: { color: colors.textPrimary, fontSize: 16, fontWeight: '700', letterSpacing: 0.3 },
  bottom: { paddingBottom: spacing.lg, gap: spacing.md },
  eyebrow: { color: colors.primary, fontSize: 11, fontWeight: '700', letterSpacing: 2 },
  title: { color: colors.textPrimary, fontSize: 44, fontWeight: '800', lineHeight: 48, letterSpacing: -1.2, marginTop: spacing.xs },
  subtitle: { color: colors.textSecondary, fontSize: 16, lineHeight: 24, marginBottom: spacing.md, maxWidth: 380 },
  primaryBtn: {
    backgroundColor: colors.primary,
    paddingVertical: 18,
    borderRadius: radii.full,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.sm,
    boxShadow: shadows.primaryLg,
    elevation: 8,
  },
  primaryBtnText: { color: '#fff', fontSize: 17, fontWeight: '700' },
  secondaryBtn: { paddingVertical: 14, alignItems: 'center' },
  secondaryBtnText: { color: colors.textSecondary, fontSize: 14, fontWeight: '500' },
});
