import { View, Text, StyleSheet, ScrollView, ActivityIndicator, TouchableOpacity, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { Feather } from '@expo/vector-icons';
import { colors, spacing, radii } from '../../src/theme';
import { api } from '../../src/api';
import { useI18n } from '../../src/i18n/I18nProvider';

export default function GoalDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { t, locale } = useI18n();
  const [goal, setGoal] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [replanning, setReplanning] = useState(false);
  const [dismissedFeasibility, setDismissedFeasibility] = useState(false);

  async function load() {
    try {
      const { data } = await api.get(`/goals/${id}`);
      setGoal(data);
    } catch { router.back(); }
    finally { setLoading(false); }
  }
  useEffect(() => { load(); }, [id]);

  async function onDelete() {
    Alert.alert(t('delete_goal'), t('delete_confirm'), [
      { text: t('cancel'), style: 'cancel' },
      {
        text: t('delete'), style: 'destructive', onPress: async () => {
          await api.delete(`/goals/${id}`);
          router.replace('/(tabs)/goals');
        },
      },
    ]);
  }

  async function applyReplan(newDeadline: string) {
    setReplanning(true);
    try {
      const { data } = await api.post(`/goals/${id}/replan`, { deadline: newDeadline });
      setGoal(data);
      setDismissedFeasibility(true);
      Alert.alert(t('plan_updated'), t('plan_updated_msg'));
    } catch (e: any) {
      const d = e?.response?.data?.detail;
      Alert.alert(t('oops'), typeof d === 'string' ? d : t('replan_failed'));
    } finally { setReplanning(false); }
  }

  if (loading) return <View style={styles.center}><ActivityIndicator color={colors.primary} size="large" /></View>;
  if (!goal) return null;

  const plan = goal.plan || {};
  const milestones = plan.milestones || [];
  const weekly = plan.weekly_plan || [];
  const feasibility: 'ok' | 'tight' | 'unrealistic' | undefined = plan.feasibility;
  const suggested = plan.suggested_deadline_iso;
  const showFeasibility =
    !dismissedFeasibility &&
    (feasibility === 'tight' || feasibility === 'unrealistic') &&
    suggested && suggested !== goal.deadline;
  const feasibilityColor = feasibility === 'unrealistic' ? colors.error : colors.warning;
  const feasibilityBg = feasibility === 'unrealistic' ? 'rgba(239,68,68,0.1)' : 'rgba(245,158,11,0.1)';
  const feasibilityBorder = feasibility === 'unrealistic' ? 'rgba(239,68,68,0.35)' : 'rgba(245,158,11,0.35)';

  function fmtDate(iso: string) {
    try { return new Date(iso).toLocaleDateString(locale, { month: 'short', day: 'numeric', year: 'numeric' }); }
    catch { return iso; }
  }

  return (
    <SafeAreaView style={styles.root} edges={['top', 'bottom']}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <View style={styles.topRow}>
          <TouchableOpacity onPress={() => router.back()} style={styles.iconBtn} testID="goal-back-btn">
            <Feather name="arrow-left" size={22} color={colors.textPrimary} />
          </TouchableOpacity>
          <TouchableOpacity onPress={onDelete} style={styles.iconBtn} testID="goal-delete-btn">
            <Feather name="trash-2" size={18} color={colors.error} />
          </TouchableOpacity>
        </View>

        <Text style={styles.eyebrow}>{t('goal')}</Text>
        <Text style={styles.title} testID="goal-title">{goal.title}</Text>
        <View style={styles.metaRow}>
          <Feather name="calendar" size={13} color={colors.textTertiary} />
          <Text style={styles.meta}>{t('due', { date: goal.deadline })}</Text>
          <Text style={styles.meta}>• {goal.hours_per_week}h/wk</Text>
          <Text style={styles.meta}>• {goal.current_level}</Text>
        </View>

        {showFeasibility ? (
          <View style={[styles.feasCard, { backgroundColor: feasibilityBg, borderColor: feasibilityBorder }]} testID="feasibility-banner">
            <View style={styles.aiRow}>
              <Feather name="alert-triangle" size={16} color={feasibilityColor} />
              <Text style={[styles.aiLabel, { color: feasibilityColor }]}>
                {feasibility === 'unrealistic' ? t('deadline_unrealistic') : t('deadline_tight')}
              </Text>
            </View>
            {plan.feasibility_reason ? (
              <Text style={styles.feasReason}>{plan.feasibility_reason}</Text>
            ) : null}
            <Text style={styles.feasSuggested}>
              {t('suggested_deadline_label')}: <Text style={{ color: colors.textPrimary, fontWeight: '700' }}>{fmtDate(suggested)}</Text>
            </Text>
            <View style={styles.feasBtnRow}>
              <TouchableOpacity
                style={[styles.feasBtn, styles.feasBtnGhost]}
                onPress={() => setDismissedFeasibility(true)}
                disabled={replanning}
                testID="feasibility-keep-btn"
              >
                <Text style={styles.feasBtnGhostText}>{t('keep_my_deadline')}</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.feasBtn, styles.feasBtnPrimary]}
                onPress={() => applyReplan(suggested)}
                disabled={replanning}
                testID="feasibility-apply-btn"
              >
                {replanning ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <>
                    <Feather name="refresh-cw" size={14} color="#fff" />
                    <Text style={styles.feasBtnPrimaryText}>{t('use_suggested')}</Text>
                  </>
                )}
              </TouchableOpacity>
            </View>
          </View>
        ) : null}

        {plan.summary ? (
          <View style={styles.aiCard} testID="goal-ai-summary">
            <View style={styles.aiRow}>
              <Feather name="cpu" size={14} color={colors.secondary} />
              <Text style={styles.aiLabel}>{t('ai_summary')}</Text>
            </View>
            <Text style={styles.aiText}>{plan.summary}</Text>
          </View>
        ) : null}

        {plan.why_it_works ? (
          <View style={[styles.aiCard, { borderColor: 'rgba(0,240,255,0.3)' }]}>
            <View style={styles.aiRow}>
              <Feather name="zap" size={14} color={colors.secondary} />
              <Text style={styles.aiLabel}>{t('why_this_works')}</Text>
            </View>
            <Text style={styles.aiText}>{plan.why_it_works}</Text>
          </View>
        ) : null}

        <Text style={styles.section}>{t('milestones')}</Text>
        {milestones.length === 0 ? (
          <Text style={styles.empty}>{t('no_milestones')}</Text>
        ) : milestones.map((m: any, i: number) => (
          <View key={i} style={styles.milestoneCard} testID={`milestone-${i}`}>
            <View style={styles.mlBullet}>
              <Text style={styles.mlNum}>{i + 1}</Text>
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.mlTitle}>{m.title}</Text>
              {m.target_date ? <Text style={styles.mlDate}>{t('target', { date: m.target_date })}</Text> : null}
              {m.description ? <Text style={styles.mlDesc}>{m.description}</Text> : null}
            </View>
          </View>
        ))}

        <Text style={styles.section}>{t('weekly_plan')}</Text>
        {weekly.length === 0 ? (
          <Text style={styles.empty}>{t('no_weekly')}</Text>
        ) : weekly.map((w: any, i: number) => (
          <View key={i} style={styles.weekCard} testID={`week-${i}`}>
            <Text style={styles.weekNum}>{t('week_n', { n: w.week })}</Text>
            <Text style={styles.weekFocus}>{w.focus}</Text>
            {(w.goals || []).map((g: string, j: number) => (
              <View key={j} style={styles.weekGoalRow}>
                <View style={styles.weekDot} />
                <Text style={styles.weekGoal}>{g}</Text>
              </View>
            ))}
          </View>
        ))}

        <View style={{ height: 40 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  center: { flex: 1, backgroundColor: colors.bg, alignItems: 'center', justifyContent: 'center' },
  scroll: { padding: spacing.lg, paddingBottom: 40 },
  topRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: spacing.md },
  iconBtn: { width: 40, height: 40, borderRadius: 20, backgroundColor: colors.surface, alignItems: 'center', justifyContent: 'center' },
  eyebrow: { color: colors.primary, fontSize: 11, fontWeight: '700', letterSpacing: 2 },
  title: { color: colors.textPrimary, fontSize: 28, fontWeight: '800', letterSpacing: -0.5, marginTop: spacing.xs },
  metaRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: spacing.sm, marginBottom: spacing.lg, flexWrap: 'wrap' },
  meta: { color: colors.textTertiary, fontSize: 13 },
  aiCard: { backgroundColor: colors.surface, borderRadius: radii.lg, padding: spacing.md, marginBottom: spacing.md, borderWidth: 1, borderColor: colors.border },
  aiRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 6 },
  aiLabel: { color: colors.textTertiary, fontSize: 11, fontWeight: '700', letterSpacing: 1.5 },
  aiText: { color: colors.textPrimary, fontSize: 15, lineHeight: 22 },
  section: { color: colors.textPrimary, fontSize: 18, fontWeight: '700', marginTop: spacing.lg, marginBottom: spacing.md },
  empty: { color: colors.textTertiary, fontStyle: 'italic' },
  milestoneCard: { flexDirection: 'row', gap: spacing.md, backgroundColor: colors.surface, borderRadius: radii.md, padding: spacing.md, marginBottom: spacing.sm, borderWidth: 1, borderColor: colors.border },
  mlBullet: { width: 32, height: 32, borderRadius: 16, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center' },
  mlNum: { color: '#fff', fontWeight: '800' },
  mlTitle: { color: colors.textPrimary, fontSize: 15, fontWeight: '700' },
  mlDate: { color: colors.secondary, fontSize: 12, marginTop: 2, fontWeight: '600' },
  mlDesc: { color: colors.textSecondary, fontSize: 13, marginTop: 4, lineHeight: 18 },
  weekCard: { backgroundColor: colors.surface, borderRadius: radii.md, padding: spacing.md, marginBottom: spacing.sm, borderWidth: 1, borderColor: colors.border },
  weekNum: { color: colors.primary, fontSize: 11, fontWeight: '800', letterSpacing: 2 },
  weekFocus: { color: colors.textPrimary, fontSize: 16, fontWeight: '700', marginTop: 2, marginBottom: spacing.sm },
  weekGoalRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 8, marginTop: 4 },
  weekDot: { width: 6, height: 6, borderRadius: 3, backgroundColor: colors.textTertiary, marginTop: 8 },
  weekGoal: { color: colors.textSecondary, fontSize: 14, flex: 1, lineHeight: 20 },
  feasCard: { borderRadius: radii.lg, padding: spacing.md, marginBottom: spacing.md, borderWidth: 1 },
  feasReason: { color: colors.textPrimary, fontSize: 14, lineHeight: 20, marginTop: 6, marginBottom: spacing.sm },
  feasSuggested: { color: colors.textSecondary, fontSize: 13, marginBottom: spacing.md },
  feasBtnRow: { flexDirection: 'row', gap: spacing.sm },
  feasBtn: { flex: 1, paddingVertical: 12, borderRadius: radii.full, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6 },
  feasBtnGhost: { borderWidth: 1, borderColor: colors.border },
  feasBtnGhostText: { color: colors.textSecondary, fontWeight: '700', fontSize: 13 },
  feasBtnPrimary: { backgroundColor: colors.primary },
  feasBtnPrimaryText: { color: '#fff', fontWeight: '700', fontSize: 13 },
});
