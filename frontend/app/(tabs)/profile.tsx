import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Feather } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { colors, spacing, radii } from '../../src/theme';
import { useAuth } from '../../src/AuthContext';

export default function Profile() {
  const { user, logout } = useAuth();
  const router = useRouter();

  const plan = user?.plan || 'free';

  return (
    <SafeAreaView style={styles.root} edges={['top']}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.title}>Profile</Text>

        <View style={styles.card}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>{(user?.name?.[0] || 'U').toUpperCase()}</Text>
          </View>
          <Text style={styles.name} testID="profile-name">{user?.name}</Text>
          <Text style={styles.email}>{user?.email}</Text>
          <View style={[styles.planBadge, plan !== 'free' && styles.planBadgePro]}>
            <Feather name={plan === 'free' ? 'star' : 'zap'} size={12} color={plan === 'free' ? colors.textSecondary : '#fff'} />
            <Text style={[styles.planText, plan !== 'free' && { color: '#fff' }]}>{plan.toUpperCase()} PLAN</Text>
          </View>
        </View>

        <TouchableOpacity style={styles.upgradeCard} onPress={() => router.push('/pricing')} testID="profile-upgrade-btn">
          <View style={{ flex: 1 }}>
            <Text style={styles.upgradeEyebrow}>UPGRADE</Text>
            <Text style={styles.upgradeTitle}>Unlock unlimited goals & daily coaching</Text>
            <Text style={styles.upgradeSub}>Pro & Coach plans from $12/month</Text>
          </View>
          <Feather name="arrow-right" size={22} color="#fff" />
        </TouchableOpacity>

        <Text style={styles.sectionTitle}>Settings</Text>
        <View style={styles.row}>
          <Feather name="bell" size={18} color={colors.textPrimary} />
          <View style={{ flex: 1 }}>
            <Text style={styles.rowText}>Smart reminders</Text>
            <Text style={styles.rowSub}>Daily nudges for your tasks</Text>
          </View>
          <View style={[styles.toggle, styles.toggleOn]}><View style={[styles.knob, styles.knobOn]} /></View>
        </View>
        <View style={styles.row}>
          <Feather name="calendar" size={18} color={colors.textPrimary} />
          <View style={{ flex: 1 }}>
            <Text style={styles.rowText}>Calendar sync</Text>
            <Text style={styles.rowSub}>Pro — coming soon</Text>
          </View>
          <Feather name="lock" size={16} color={colors.textTertiary} />
        </View>

        <TouchableOpacity style={styles.logout} onPress={logout} testID="profile-logout-btn">
          <Feather name="log-out" size={16} color={colors.error} />
          <Text style={styles.logoutText}>Log out</Text>
        </TouchableOpacity>

        <Text style={styles.footer}>GoalPilot AI · v1.0</Text>
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
  upgradeCard: { flexDirection: 'row', alignItems: 'center', gap: spacing.md, backgroundColor: colors.primary, borderRadius: radii.lg, padding: spacing.md, marginBottom: spacing.xl, shadowColor: colors.primary, shadowOpacity: 0.5, shadowRadius: 14 },
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
