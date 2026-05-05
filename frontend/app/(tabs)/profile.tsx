import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Alert, Platform, Linking } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Feather } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import * as WebBrowser from 'expo-web-browser';
import { colors, spacing, radii, shadows } from '../../src/theme';
import { useAuth } from '../../src/AuthContext';
import { api } from '../../src/api';
import { useState } from 'react';
import { useI18n } from '../../src/i18n/I18nProvider';

const BACKEND = process.env.EXPO_PUBLIC_BACKEND_URL;

export default function Profile() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const { t, locale, supported } = useI18n();
  const [syncing, setSyncing] = useState(false);

  const plan = user?.plan || 'free';
  const planLabel = plan === 'free' ? t('free_plan') : plan === 'pro' ? t('pro_plan') : t('coach_plan');
  const currentLangLabel = supported.find(s => s.code === locale)?.label || 'English (US)';

  async function syncCalendar() {
    setSyncing(true);
    try {
      const { data } = await api.get('/calendar/url');
      const url = `${BACKEND}/api/calendar/export.ics?token=${data.token}`;
      if (Platform.OS === 'web') {
        window.open(url, '_blank');
      } else {
        const webcal = url.replace(/^https?:\/\//, 'webcal://');
        const supported = await Linking.canOpenURL(webcal);
        if (supported) await Linking.openURL(webcal);
        else await WebBrowser.openBrowserAsync(url);
      }
      Alert.alert(t('sync_calendar'), t('sync_calendar_done'));
    } catch {
      Alert.alert(t('oops'), t('could_not_calendar'));
    } finally { setSyncing(false); }
  }

  return (
    <SafeAreaView style={styles.root} edges={['top']}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.title}>{t('profile')}</Text>

        <View style={styles.card}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>{(user?.name?.[0] || 'U').toUpperCase()}</Text>
          </View>
          <Text style={styles.name} testID="profile-name">{user?.name}</Text>
          <Text style={styles.email}>{user?.email}</Text>
          <View style={[styles.planBadge, plan !== 'free' && styles.planBadgePro]}>
            <Feather name={plan === 'free' ? 'star' : 'zap'} size={12} color={plan === 'free' ? colors.textSecondary : '#fff'} />
            <Text style={[styles.planText, plan !== 'free' && { color: '#fff' }]}>{planLabel}</Text>
          </View>
        </View>

        <TouchableOpacity style={styles.upgradeCard} onPress={() => router.push('/pricing')} testID="profile-upgrade-btn">
          <View style={{ flex: 1 }}>
            <Text style={styles.upgradeEyebrow}>{t('upgrade')}</Text>
            <Text style={styles.upgradeTitle}>{t('upgrade_title')}</Text>
            <Text style={styles.upgradeSub}>{t('upgrade_sub')}</Text>
          </View>
          <Feather name="arrow-right" size={22} color="#fff" />
        </TouchableOpacity>

        <Text style={styles.sectionTitle}>{t('settings')}</Text>

        <TouchableOpacity style={styles.row} onPress={syncCalendar} disabled={syncing} testID="profile-calendar-btn">
          <Feather name="calendar" size={18} color={colors.textPrimary} />
          <View style={{ flex: 1 }}>
            <Text style={styles.rowText}>{t('sync_calendar')}</Text>
            <Text style={styles.rowSub}>{t('sync_calendar_sub')}</Text>
          </View>
          <Feather name={syncing ? 'loader' : 'external-link'} size={16} color={colors.textTertiary} />
        </TouchableOpacity>

        <TouchableOpacity style={styles.row} onPress={() => router.push('/settings/language')} testID="profile-language-btn">
          <Feather name="globe" size={18} color={colors.textPrimary} />
          <View style={{ flex: 1 }}>
            <Text style={styles.rowText}>{t('language')}</Text>
            <Text style={styles.rowSub}>{currentLangLabel}</Text>
          </View>
          <Feather name="chevron-right" size={16} color={colors.textTertiary} />
        </TouchableOpacity>

        <View style={styles.row}>
          <Feather name="bell" size={18} color={colors.textPrimary} />
          <View style={{ flex: 1 }}>
            <Text style={styles.rowText}>{t('smart_reminders')}</Text>
            <Text style={styles.rowSub}>{t('smart_reminders_sub')}</Text>
          </View>
          <View style={[styles.toggle, styles.toggleOn]}><View style={[styles.knob, styles.knobOn]} /></View>
        </View>

        <TouchableOpacity style={styles.logout} onPress={logout} testID="profile-logout-btn">
          <Feather name="log-out" size={16} color={colors.error} />
          <Text style={styles.logoutText}>{t('log_out')}</Text>
        </TouchableOpacity>

        <Text style={styles.footer}>GoalPilot AI · v1.1</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  scroll: { padding: spacing.lg, paddingBottom: 40 },
  title: { color: colors.textPrimary, fontSize: 30, fontWeight: '800', letterSpacing: -0.5, marginBottom: spacing.lg },
  card: { backgroundColor: colors.surface, borderRadius: radii.lg, padding: spacing.lg, alignItems: 'center', borderWidth: 1, borderColor: colors.border, marginBottom: spacing.md },
  avatar: { width: 72, height: 72, borderRadius: 36, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center', marginBottom: spacing.md },
  avatarText: { color: '#fff', fontSize: 28, fontWeight: '800' },
  name: { color: colors.textPrimary, fontSize: 20, fontWeight: '700' },
  email: { color: colors.textSecondary, fontSize: 14, marginTop: 2 },
  planBadge: { flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: colors.surfaceElev, paddingVertical: 6, paddingHorizontal: 12, borderRadius: radii.full, marginTop: spacing.md },
  planBadgePro: { backgroundColor: colors.primary },
  planText: { color: colors.textSecondary, fontSize: 11, fontWeight: '700', letterSpacing: 1 },
  upgradeCard: { flexDirection: 'row', alignItems: 'center', gap: spacing.md, backgroundColor: colors.primary, borderRadius: radii.lg, padding: spacing.md, marginBottom: spacing.xl, boxShadow: shadows.primaryMd },
  upgradeEyebrow: { color: 'rgba(255,255,255,0.8)', fontSize: 10, fontWeight: '700', letterSpacing: 2 },
  upgradeTitle: { color: '#fff', fontSize: 16, fontWeight: '700', marginTop: 4 },
  upgradeSub: { color: 'rgba(255,255,255,0.8)', fontSize: 13, marginTop: 2 },
  sectionTitle: { color: colors.textPrimary, fontSize: 16, fontWeight: '700', marginBottom: spacing.md },
  row: { flexDirection: 'row', alignItems: 'center', gap: spacing.md, backgroundColor: colors.surface, borderRadius: radii.md, padding: spacing.md, marginBottom: spacing.sm, borderWidth: 1, borderColor: colors.border },
  rowText: { color: colors.textPrimary, fontSize: 15, fontWeight: '600' },
  rowSub: { color: colors.textTertiary, fontSize: 12, marginTop: 2 },
  toggle: { width: 44, height: 26, borderRadius: 13, backgroundColor: colors.surfaceElev, padding: 3 },
  toggleOn: { backgroundColor: colors.primary },
  knob: { width: 20, height: 20, borderRadius: 10, backgroundColor: colors.textPrimary },
  knobOn: { transform: [{ translateX: 18 }] },
  logout: { flexDirection: 'row', alignItems: 'center', gap: 8, justifyContent: 'center', paddingVertical: 14, marginTop: spacing.md },
  logoutText: { color: colors.error, fontWeight: '700' },
  footer: { color: colors.textTertiary, fontSize: 12, textAlign: 'center', marginTop: spacing.md },
});
