import { View, Text, StyleSheet, ScrollView, TouchableOpacity, RefreshControl, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter, useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { Feather } from '@expo/vector-icons';
import { colors, spacing, radii } from '../../src/theme';
import { api } from '../../src/api';
import { useAuth } from '../../src/AuthContext';
import ProgressRing from '../../src/ProgressRing';

type Task = { id: string; title: string; priority: string; est_minutes: number; completed: boolean; goal_id: string; due_date: string };
type Stats = { today_total: number; today_done: number; today_pct: number; active_goals: number; total_completed: number; missed: number; streak: number };
type Nudge = { show: boolean; title?: string; message?: string; days_since?: number | null; suggested_task?: Task | null };

export default function Dashboard() {
  const router = useRouter();
  const { user } = useAuth();
  const [stats, setStats] = useState<Stats | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [missed, setMissed] = useState<Task[]>([]);
  const [nudge, setNudge] = useState<Nudge | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  async function load() {
    try {
      const [s, t, m, n] = await Promise.all([
        api.get('/dashboard/stats'),
        api.get('/tasks/today'),
        api.get('/tasks/missed'),
        api.get('/nudge'),
      ]);
      setStats(s.data);
      setTasks(t.data);
      setMissed(m.data);
      setNudge(n.data);
    } catch (e) { console.log('load err', e); }
    finally { setLoading(false); setRefreshing(false); }
  }

  async function doQuickWin() {
    if (!nudge?.suggested_task) return;
    const task = nudge.suggested_task;
    try {
      await api.patch(`/tasks/${task.id}`, { completed: true });
      load();
    } catch {}
  }

  useFocusEffect(useCallback(() => { load(); }, []));

  async function toggleTask(task: Task) {
    const next = !task.completed;
    setTasks(tasks.map(x => x.id === task.id ? { ...x, completed: next } : x));
    try {
      await api.patch(`/tasks/${task.id}`, { completed: next });
      load();
    } catch {
      setTasks(tasks);
    }
  }

  if (loading) {
    return <View style={styles.center}><ActivityIndicator color={colors.primary} size="large" /></View>;
  }

  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';
  const today = new Date().toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' });

  return (
    <SafeAreaView style={styles.root} edges={['top']}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} tintColor={colors.primary} />}
      >
        <View style={styles.header}>
          <View>
            <Text style={styles.date}>{today}</Text>
            <Text style={styles.greeting} testID="dashboard-greeting">{greeting}, {user?.name?.split(' ')[0] || 'there'}</Text>
          </View>
          <TouchableOpacity style={styles.addBtn} onPress={() => router.push('/goal/new')} testID="dashboard-new-goal-btn">
            <Feather name="plus" size={20} color="#fff" />
          </TouchableOpacity>
        </View>

        <View style={styles.statsRow}>
          <View style={styles.ringCard}>
            <ProgressRing percent={stats?.today_pct ?? 0} label={`${stats?.today_done ?? 0}/${stats?.today_total ?? 0} today`} />
          </View>
          <View style={styles.statsCol}>
            <View style={styles.statCard}>
              <Feather name="zap" size={18} color={colors.primary} />
              <Text style={styles.statValue} testID="dashboard-streak">{stats?.streak ?? 0}</Text>
              <Text style={styles.statLabel}>Day streak</Text>
            </View>
            <View style={styles.statCard}>
              <Feather name="target" size={18} color={colors.secondary} />
              <Text style={styles.statValue}>{stats?.active_goals ?? 0}</Text>
              <Text style={styles.statLabel}>Active goals</Text>
            </View>
          </View>
        </View>

        {nudge?.show ? (
          <View style={styles.nudgeCard} testID="nudge-card">
            <View style={styles.nudgeRow}>
              <Feather name="life-buoy" size={18} color={colors.secondary} />
              <Text style={styles.nudgeTitle}>{nudge.title}</Text>
            </View>
            <Text style={styles.nudgeMsg}>{nudge.message}</Text>
            {nudge.suggested_task ? (
              <TouchableOpacity testID="nudge-quick-win" style={styles.nudgeBtn} onPress={doQuickWin}>
                <Feather name="zap" size={14} color={colors.bg} />
                <Text style={styles.nudgeBtnText}>Do this one: {nudge.suggested_task.title}</Text>
              </TouchableOpacity>
            ) : null}
          </View>
        ) : null}

        {(missed && missed.length > 0) ? (
          <View style={styles.alertCard}>
            <View style={styles.alertRow}>
              <Feather name="alert-circle" size={18} color={colors.warning} />
              <Text style={styles.alertTitle}>{missed.length} missed task{missed.length > 1 ? 's' : ''}</Text>
            </View>
            <Text style={styles.alertSub}>Tap a task below to catch up, or we&apos;ll adapt your plan next week.</Text>
          </View>
        ) : null}

        <Text style={styles.sectionTitle}>Today&apos;s Action Plan</Text>

        {tasks.length === 0 ? (
          <View style={styles.emptyCard} testID="dashboard-empty">
            <Feather name="coffee" size={32} color={colors.textTertiary} />
            <Text style={styles.emptyTitle}>No tasks for today</Text>
            <Text style={styles.emptySub}>Create a goal and let GoalPilot AI generate your daily plan.</Text>
            <TouchableOpacity style={styles.emptyBtn} onPress={() => router.push('/goal/new')} testID="dashboard-create-goal-btn">
              <Text style={styles.emptyBtnText}>Create your first goal</Text>
            </TouchableOpacity>
          </View>
        ) : tasks.map(task => (
          <TouchableOpacity
            key={task.id}
            testID={`task-${task.id}`}
            activeOpacity={0.8}
            style={[styles.taskCard, task.completed && styles.taskDone]}
            onPress={() => toggleTask(task)}
          >
            <View style={[styles.checkbox, task.completed && styles.checkboxDone]}>
              {task.completed ? <Feather name="check" size={14} color="#fff" /> : null}
            </View>
            <View style={{ flex: 1 }}>
              <Text style={[styles.taskTitle, task.completed && styles.taskTitleDone]}>{task.title}</Text>
              <View style={styles.taskMeta}>
                <View style={[styles.priorityDot, { backgroundColor: task.priority === 'high' ? colors.error : task.priority === 'medium' ? colors.warning : colors.secondary }]} />
                <Text style={styles.taskMetaText}>{task.priority}</Text>
                <Text style={styles.taskMetaText}>• {task.est_minutes} min</Text>
              </View>
            </View>
          </TouchableOpacity>
        ))}

        {missed.slice(0, 5).map(task => (
          <TouchableOpacity
            key={task.id}
            testID={`missed-task-${task.id}`}
            activeOpacity={0.8}
            style={[styles.taskCard, styles.taskMissed]}
            onPress={() => toggleTask(task)}
          >
            <View style={styles.checkbox} />
            <View style={{ flex: 1 }}>
              <Text style={styles.taskTitle}>{task.title}</Text>
              <Text style={styles.missedLabel}>Missed • {task.due_date}</Text>
            </View>
          </TouchableOpacity>
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
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: spacing.lg },
  date: { color: colors.textTertiary, fontSize: 13, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 1 },
  greeting: { color: colors.textPrimary, fontSize: 28, fontWeight: '800', letterSpacing: -0.5, marginTop: 4 },
  addBtn: { width: 44, height: 44, borderRadius: 22, backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center', shadowColor: colors.primary, shadowOpacity: 0.5, shadowRadius: 10 },
  statsRow: { flexDirection: 'row', gap: spacing.md, marginBottom: spacing.lg },
  ringCard: { backgroundColor: colors.surface, borderRadius: radii.lg, padding: spacing.md, flex: 1.2, alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: colors.border },
  statsCol: { flex: 1, gap: spacing.sm },
  statCard: { backgroundColor: colors.surface, borderRadius: radii.md, padding: spacing.md, flex: 1, borderWidth: 1, borderColor: colors.border },
  statValue: { color: colors.textPrimary, fontSize: 28, fontWeight: '800', marginTop: 4 },
  statLabel: { color: colors.textSecondary, fontSize: 12 },
  alertCard: { backgroundColor: 'rgba(245, 158, 11, 0.1)', borderWidth: 1, borderColor: 'rgba(245, 158, 11, 0.3)', borderRadius: radii.md, padding: spacing.md, marginBottom: spacing.md },
  alertRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  alertTitle: { color: colors.warning, fontWeight: '700', fontSize: 14 },
  alertSub: { color: colors.textSecondary, fontSize: 13, marginTop: 4 },
  sectionTitle: { color: colors.textPrimary, fontSize: 18, fontWeight: '700', marginBottom: spacing.md, marginTop: spacing.sm },
  emptyCard: { backgroundColor: colors.surface, borderRadius: radii.lg, padding: spacing.xl, alignItems: 'center', borderWidth: 1, borderColor: colors.border, gap: spacing.sm },
  emptyTitle: { color: colors.textPrimary, fontSize: 18, fontWeight: '700', marginTop: 8 },
  emptySub: { color: colors.textSecondary, textAlign: 'center', fontSize: 14, marginBottom: spacing.md },
  emptyBtn: { backgroundColor: colors.primary, paddingVertical: 12, paddingHorizontal: 20, borderRadius: radii.full },
  emptyBtnText: { color: '#fff', fontWeight: '700' },
  taskCard: { flexDirection: 'row', alignItems: 'center', gap: spacing.md, backgroundColor: colors.surface, borderRadius: radii.md, padding: spacing.md, marginBottom: spacing.sm, borderWidth: 1, borderColor: colors.border },
  taskDone: { opacity: 0.55 },
  taskMissed: { borderColor: 'rgba(245, 158, 11, 0.3)' },
  checkbox: { width: 24, height: 24, borderRadius: 12, borderWidth: 2, borderColor: colors.textTertiary, alignItems: 'center', justifyContent: 'center' },
  checkboxDone: { borderColor: colors.primary, backgroundColor: colors.primary },
  taskTitle: { color: colors.textPrimary, fontSize: 15, fontWeight: '600' },
  taskTitleDone: { textDecorationLine: 'line-through', color: colors.textSecondary },
  taskMeta: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 4 },
  priorityDot: { width: 6, height: 6, borderRadius: 3 },
  taskMetaText: { color: colors.textTertiary, fontSize: 12, fontWeight: '500', textTransform: 'capitalize' },
  missedLabel: { color: colors.warning, fontSize: 12, marginTop: 4 },
  nudgeCard: { backgroundColor: 'rgba(0,240,255,0.08)', borderWidth: 1, borderColor: 'rgba(0,240,255,0.35)', borderRadius: radii.lg, padding: spacing.md, marginBottom: spacing.md },
  nudgeRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm, marginBottom: 4 },
  nudgeTitle: { color: colors.secondary, fontWeight: '800', fontSize: 15 },
  nudgeMsg: { color: colors.textPrimary, fontSize: 14, lineHeight: 20, marginTop: 2, marginBottom: spacing.sm },
  nudgeBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, backgroundColor: colors.secondary, paddingVertical: 10, borderRadius: radii.full },
  nudgeBtnText: { color: colors.bg, fontWeight: '800', fontSize: 13 },
});
