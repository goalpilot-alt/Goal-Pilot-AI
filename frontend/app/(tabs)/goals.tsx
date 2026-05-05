import { View, Text, StyleSheet, ScrollView, TouchableOpacity, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter, useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { Feather } from '@expo/vector-icons';
import { colors, spacing, radii } from '../../src/theme';
import { api } from '../../src/api';
import { useI18n } from '../../src/i18n/I18nProvider';

type Goal = { id: string; title: string; deadline: string; status: string; plan?: any };

export default function Goals() {
  const router = useRouter();
  const { t } = useI18n();
  const [goals, setGoals] = useState<Goal[]>([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    try {
      const { data } = await api.get('/goals');
      setGoals(data);
    } catch {}
    finally { setLoading(false); }
  }

  useFocusEffect(useCallback(() => { load(); }, []));

  if (loading) return <View style={styles.center}><ActivityIndicator color={colors.primary} size="large" /></View>;

  return (
    <SafeAreaView style={styles.root} edges={['top']}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <View style={styles.header}>
          <Text style={styles.title}>{t('your_goals')}</Text>
          <TouchableOpacity style={styles.addBtn} onPress={() => router.push('/goal/new')} testID="goals-new-btn">
            <Feather name="plus" size={20} color="#fff" />
          </TouchableOpacity>
        </View>

        {goals.length === 0 ? (
          <View style={styles.empty} testID="goals-empty">
            <Feather name="flag" size={40} color={colors.textTertiary} />
            <Text style={styles.emptyTitle}>{t('no_goals_yet')}</Text>
            <Text style={styles.emptySub}>{t('no_goals_sub')}</Text>
            <TouchableOpacity style={styles.emptyBtn} onPress={() => router.push('/goal/new')}>
              <Text style={styles.emptyBtnText}>{t('create_a_goal')}</Text>
            </TouchableOpacity>
          </View>
        ) : goals.map(g => (
          <TouchableOpacity
            key={g.id}
            testID={`goal-card-${g.id}`}
            activeOpacity={0.85}
            style={styles.card}
            onPress={() => router.push(`/goal/${g.id}`)}
          >
            <View style={styles.cardTop}>
              <View style={[styles.badge, g.status === 'active' ? styles.badgeActive : styles.badgeDone]}>
                <Text style={styles.badgeText}>{g.status}</Text>
              </View>
              <Feather name="chevron-right" size={18} color={colors.textTertiary} />
            </View>
            <Text style={styles.cardTitle}>{g.title}</Text>
            <View style={styles.cardMeta}>
              <Feather name="calendar" size={13} color={colors.textTertiary} />
              <Text style={styles.cardMetaText}>{t('due', { date: g.deadline })}</Text>
              {g.plan?.milestones ? (
                <Text style={styles.cardMetaText}>• {t('milestones_count', { n: g.plan.milestones.length })}</Text>
              ) : null}
            </View>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  center: { flex: 1, backgroundColor: colors.bg, alignItems: 'center', justifyContent: 'center' },
  scroll: { padding: spacing.lg, paddingBottom: 40 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.lg },
  title: { color: colors.textPrimary, fontSize: 30, fontWeight: '800', letterSpacing: -0.5 },
  addBtn: { width: 44, height: 44, borderRadius: 22, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center' },
  empty: { backgroundColor: colors.surface, borderRadius: radii.lg, padding: spacing.xl, alignItems: 'center', borderWidth: 1, borderColor: colors.border, gap: spacing.sm, marginTop: spacing.xl },
  emptyTitle: { color: colors.textPrimary, fontSize: 20, fontWeight: '700', marginTop: 8 },
  emptySub: { color: colors.textSecondary, textAlign: 'center', marginBottom: spacing.md },
  emptyBtn: { backgroundColor: colors.primary, paddingVertical: 12, paddingHorizontal: 20, borderRadius: radii.full },
  emptyBtnText: { color: '#fff', fontWeight: '700' },
  card: { backgroundColor: colors.surface, borderRadius: radii.lg, padding: spacing.md, marginBottom: spacing.md, borderWidth: 1, borderColor: colors.border },
  cardTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: spacing.sm },
  badge: { paddingVertical: 4, paddingHorizontal: 10, borderRadius: radii.full },
  badgeActive: { backgroundColor: 'rgba(255, 94, 0, 0.15)' },
  badgeDone: { backgroundColor: 'rgba(16, 185, 129, 0.15)' },
  badgeText: { color: colors.primary, fontSize: 11, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 1 },
  cardTitle: { color: colors.textPrimary, fontSize: 18, fontWeight: '700', marginBottom: spacing.sm },
  cardMeta: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  cardMetaText: { color: colors.textTertiary, fontSize: 13 },
});
