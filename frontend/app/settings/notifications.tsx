import { View, Text, StyleSheet, ScrollView, TouchableOpacity, ActivityIndicator, Switch, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { Feather } from '@expo/vector-icons';
import { colors, spacing, radii } from '../../src/theme';
import { useI18n } from '../../src/i18n/I18nProvider';
import { api } from '../../src/api';

type Prefs = { morning: boolean; streak: boolean };

export default function NotificationsScreen() {
  const router = useRouter();
  const { t } = useI18n();
  const [prefs, setPrefs] = useState<Prefs>({ morning: true, streak: true });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get('/notifications/prefs');
        setPrefs({ morning: !!data.morning, streak: !!data.streak });
      } catch {}
      finally { setLoading(false); }
    })();
  }, []);

  async function toggle(key: keyof Prefs, value: boolean) {
    const next = { ...prefs, [key]: value };
    setPrefs(next);
    setSaving(true);
    try {
      await api.patch('/notifications/prefs', { [key]: value });
    } catch {
      setPrefs(prefs); // revert on failure
    } finally { setSaving(false); }
  }

  return (
    <SafeAreaView style={styles.root} edges={['top', 'bottom']}>
      <View style={styles.topRow}>
        <TouchableOpacity onPress={() => router.back()} style={styles.iconBtn} testID="notif-back-btn">
          <Feather name="x" size={22} color={colors.textPrimary} />
        </TouchableOpacity>
        <Text style={styles.title}>{t('notifications')}</Text>
        <View style={{ width: 40 }} />
      </View>

      {loading ? (
        <View style={styles.loader}>
          <ActivityIndicator color={colors.primary} size="large" />
        </View>
      ) : (
        <ScrollView contentContainerStyle={styles.scroll}>
          <Text style={styles.section}>{t('daily_pushes')}</Text>

          <View style={styles.row} testID="notif-row-morning">
            <View style={styles.iconCircle}>
              <Feather name="sun" size={18} color={colors.primary} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.rowTitle}>{t('morning_summary')}</Text>
              <Text style={styles.rowSub}>{t('morning_summary_sub')}</Text>
            </View>
            <Switch
              testID="notif-toggle-morning"
              value={prefs.morning}
              onValueChange={(v) => toggle('morning', v)}
              trackColor={{ false: colors.surfaceElev, true: colors.primary }}
              thumbColor={Platform.OS === 'android' ? '#fff' : undefined}
              ios_backgroundColor={colors.surfaceElev}
              disabled={saving}
            />
          </View>

          <View style={styles.row} testID="notif-row-streak">
            <View style={[styles.iconCircle, { backgroundColor: 'rgba(0,240,255,0.15)' }]}>
              <Feather name="life-buoy" size={18} color={colors.secondary} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.rowTitle}>{t('streak_nudges')}</Text>
              <Text style={styles.rowSub}>{t('streak_nudges_sub')}</Text>
            </View>
            <Switch
              testID="notif-toggle-streak"
              value={prefs.streak}
              onValueChange={(v) => toggle('streak', v)}
              trackColor={{ false: colors.surfaceElev, true: colors.primary }}
              thumbColor={Platform.OS === 'android' ? '#fff' : undefined}
              ios_backgroundColor={colors.surfaceElev}
              disabled={saving}
            />
          </View>

          <Text style={styles.foot}>{t('notif_foot')}</Text>
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  topRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: spacing.lg, paddingVertical: spacing.md },
  iconBtn: { width: 40, height: 40, borderRadius: 20, backgroundColor: colors.surface, alignItems: 'center', justifyContent: 'center' },
  title: { color: colors.textPrimary, fontSize: 18, fontWeight: '700' },
  loader: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  scroll: { padding: spacing.lg },
  section: { color: colors.textTertiary, fontSize: 11, fontWeight: '700', letterSpacing: 1.5, textTransform: 'uppercase', marginBottom: spacing.sm },
  row: { flexDirection: 'row', alignItems: 'center', gap: spacing.md, padding: spacing.md, borderRadius: radii.md, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, marginBottom: spacing.sm },
  iconCircle: { width: 38, height: 38, borderRadius: 19, backgroundColor: 'rgba(255,94,0,0.15)', alignItems: 'center', justifyContent: 'center' },
  rowTitle: { color: colors.textPrimary, fontSize: 15, fontWeight: '700' },
  rowSub: { color: colors.textTertiary, fontSize: 12, marginTop: 2 },
  foot: { color: colors.textTertiary, fontSize: 12, marginTop: spacing.lg, textAlign: 'center', fontStyle: 'italic', lineHeight: 18 },
});
