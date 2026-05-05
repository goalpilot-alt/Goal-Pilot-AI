import { View, Text, StyleSheet, ScrollView, ActivityIndicator, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useCallback, useState } from 'react';
import { useFocusEffect } from 'expo-router';
import { Feather } from '@expo/vector-icons';
import { colors, spacing, radii } from '../../src/theme';
import { api } from '../../src/api';
import { useI18n } from '../../src/i18n/I18nProvider';

type Review = { completed: number; missed: number; total_due: number; completion_rate: number; summary: string; suggestion: string };

export default function ReviewScreen() {
  const { t } = useI18n();
  const [review, setReview] = useState<Review | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const { data } = await api.get('/review/weekly');
      setReview(data);
    } catch {}
    finally { setLoading(false); }
  }

  useFocusEffect(useCallback(() => { load(); }, []));

  return (
    <SafeAreaView style={styles.root} edges={['top']}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.eyebrow}>{t('last_7_days')}</Text>
        <Text style={styles.title}>{t('weekly_review')}</Text>
        <Text style={styles.subtitle}>{t('review_subtitle')}</Text>

        {loading ? (
          <View style={styles.loaderBox}>
            <ActivityIndicator color={colors.primary} size="large" />
            <Text style={styles.loaderText}>{t('generating_insights')}</Text>
          </View>
        ) : review ? (
          <>
            <View style={styles.statsRow}>
              <View style={styles.statBox}>
                <Text style={[styles.statNum, { color: colors.success }]}>{review.completed}</Text>
                <Text style={styles.statLbl}>{t('completed')}</Text>
              </View>
              <View style={styles.statBox}>
                <Text style={[styles.statNum, { color: colors.warning }]}>{review.missed}</Text>
                <Text style={styles.statLbl}>{t('missed')}</Text>
              </View>
              <View style={styles.statBox}>
                <Text style={[styles.statNum, { color: colors.secondary }]}>{review.completion_rate}%</Text>
                <Text style={styles.statLbl}>{t('rate')}</Text>
              </View>
            </View>

            <View style={styles.aiCard} testID="review-summary-card">
              <View style={styles.aiRow}>
                <Feather name="message-circle" size={16} color={colors.secondary} />
                <Text style={styles.aiLabel}>{t('coach_summary')}</Text>
              </View>
              <Text style={styles.aiText}>{review.summary}</Text>
            </View>

            <View style={styles.aiCard}>
              <View style={styles.aiRow}>
                <Feather name="compass" size={16} color={colors.primary} />
                <Text style={styles.aiLabel}>{t('next_week_focus')}</Text>
              </View>
              <Text style={styles.aiText}>{review.suggestion}</Text>
            </View>

            <TouchableOpacity style={styles.refreshBtn} onPress={load} testID="review-refresh-btn">
              <Feather name="refresh-cw" size={16} color={colors.textPrimary} />
              <Text style={styles.refreshText}>{t('regenerate')}</Text>
            </TouchableOpacity>
          </>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  scroll: { padding: spacing.lg, paddingBottom: 40 },
  eyebrow: { color: colors.primary, fontSize: 11, fontWeight: '700', letterSpacing: 2, marginBottom: 4 },
  title: { color: colors.textPrimary, fontSize: 30, fontWeight: '800', letterSpacing: -0.5 },
  subtitle: { color: colors.textSecondary, marginTop: spacing.xs, marginBottom: spacing.lg },
  loaderBox: { alignItems: 'center', padding: spacing.xl, gap: spacing.md },
  loaderText: { color: colors.textSecondary },
  statsRow: { flexDirection: 'row', gap: spacing.sm, marginBottom: spacing.lg },
  statBox: { flex: 1, backgroundColor: colors.surface, borderRadius: radii.md, padding: spacing.md, alignItems: 'center', borderWidth: 1, borderColor: colors.border },
  statNum: { fontSize: 30, fontWeight: '800' },
  statLbl: { color: colors.textSecondary, fontSize: 12, marginTop: 4 },
  aiCard: { backgroundColor: colors.surface, borderRadius: radii.lg, padding: spacing.md, marginBottom: spacing.md, borderWidth: 1, borderColor: colors.border },
  aiRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: spacing.sm },
  aiLabel: { color: colors.textTertiary, fontSize: 11, fontWeight: '700', letterSpacing: 1.5 },
  aiText: { color: colors.textPrimary, fontSize: 15, lineHeight: 22 },
  refreshBtn: { flexDirection: 'row', gap: 8, alignSelf: 'center', paddingVertical: 12, paddingHorizontal: 20, backgroundColor: colors.surfaceElev, borderRadius: radii.full, alignItems: 'center', marginTop: spacing.md },
  refreshText: { color: colors.textPrimary, fontWeight: '600' },
});
