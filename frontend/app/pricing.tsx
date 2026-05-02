import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Feather } from '@expo/vector-icons';
import { colors, spacing, radii } from '../src/theme';
import { api } from '../src/api';
import { useAuth } from '../src/AuthContext';
import { useState } from 'react';

const PLANS = [
  {
    key: 'free',
    name: 'Free',
    price: '$0',
    features: ['1 active goal', 'Basic AI plan', 'Manual tracking', 'Basic reminders'],
    cta: 'Current',
  },
  {
    key: 'pro',
    name: 'Pro',
    price: '$12',
    highlight: true,
    features: ['Up to 5 goals', 'AI goal breakdown', 'Smart reminders', 'Calendar integration', 'Weekly AI review'],
    cta: 'Upgrade to Pro',
  },
  {
    key: 'coach',
    name: 'Coach',
    price: '$29',
    features: ['Unlimited goals', 'Daily AI coaching', 'Advanced insights', 'Accountability mode', 'Priority automation'],
    cta: 'Upgrade to Coach',
  },
];

export default function Pricing() {
  const router = useRouter();
  const { user, refreshUser } = useAuth();
  const [busy, setBusy] = useState<string | null>(null);
  const current = user?.plan || 'free';

  async function upgrade(plan: string) {
    if (plan === current) return;
    setBusy(plan);
    try {
      // NOTE: Stripe integration is MOCKED for MVP — this simulates a successful payment.
      await api.post(`/subscription/upgrade?plan=${plan}`);
      await refreshUser();
      Alert.alert('Success', `You're now on the ${plan.toUpperCase()} plan! (Stripe integration mocked for MVP)`);
    } catch (e: any) {
      Alert.alert('Oops', 'Could not complete upgrade.');
    } finally { setBusy(null); }
  }

  return (
    <SafeAreaView style={styles.root} edges={['top', 'bottom']}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <TouchableOpacity onPress={() => router.back()} style={styles.back} testID="pricing-back-btn">
          <Feather name="x" size={22} color={colors.textPrimary} />
        </TouchableOpacity>

        <Text style={styles.eyebrow}>CHOOSE YOUR PLAN</Text>
        <Text style={styles.title}>Go all-in on your goals.</Text>
        <Text style={styles.sub}>Cancel anytime. 7-day free trial on Pro & Coach.</Text>

        {PLANS.map(p => {
          const active = current === p.key;
          return (
            <View
              key={p.key}
              style={[styles.card, p.highlight && styles.cardHighlight, active && styles.cardActive]}
              testID={`plan-card-${p.key}`}
            >
              {p.highlight && (
                <View style={styles.popular}><Text style={styles.popularText}>MOST POPULAR</Text></View>
              )}
              <Text style={styles.planName}>{p.name}</Text>
              <View style={styles.priceRow}>
                <Text style={styles.price}>{p.price}</Text>
                {p.price !== '$0' && <Text style={styles.per}>/month</Text>}
              </View>
              {p.features.map((f, i) => (
                <View key={i} style={styles.featRow}>
                  <Feather name="check" size={15} color={colors.primary} />
                  <Text style={styles.featText}>{f}</Text>
                </View>
              ))}
              <TouchableOpacity
                disabled={active || busy !== null}
                style={[styles.cta, active && styles.ctaActive, p.highlight && !active && styles.ctaPrimary]}
                onPress={() => upgrade(p.key)}
                testID={`plan-cta-${p.key}`}
              >
                <Text style={[styles.ctaText, p.highlight && !active && { color: '#fff' }, active && { color: colors.textSecondary }]}>
                  {active ? 'Current plan' : busy === p.key ? 'Processing…' : p.cta}
                </Text>
              </TouchableOpacity>
            </View>
          );
        })}

        <Text style={styles.note}>Stripe payment flow is MOCKED for this MVP. Enabling real checkout requires Stripe keys.</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  scroll: { padding: spacing.lg, paddingBottom: 40 },
  back: { width: 40, height: 40, borderRadius: 20, backgroundColor: colors.surface, alignItems: 'center', justifyContent: 'center', marginBottom: spacing.lg },
  eyebrow: { color: colors.primary, fontSize: 11, fontWeight: '700', letterSpacing: 2 },
  title: { color: colors.textPrimary, fontSize: 30, fontWeight: '800', letterSpacing: -0.5, marginTop: spacing.xs },
  sub: { color: colors.textSecondary, marginTop: spacing.sm, marginBottom: spacing.lg },
  card: { backgroundColor: colors.surface, borderRadius: radii.lg, padding: spacing.lg, marginBottom: spacing.md, borderWidth: 1, borderColor: colors.border },
  cardHighlight: { borderColor: colors.primary, shadowColor: colors.primary, shadowOpacity: 0.3, shadowRadius: 20, shadowOffset: { width: 0, height: 4 } },
  cardActive: { borderColor: colors.success },
  popular: { position: 'absolute', top: -12, right: 16, backgroundColor: colors.primary, paddingVertical: 4, paddingHorizontal: 10, borderRadius: radii.full },
  popularText: { color: '#fff', fontSize: 10, fontWeight: '800', letterSpacing: 1.5 },
  planName: { color: colors.textPrimary, fontSize: 20, fontWeight: '800' },
  priceRow: { flexDirection: 'row', alignItems: 'flex-end', gap: 4, marginVertical: spacing.sm },
  price: { color: colors.textPrimary, fontSize: 38, fontWeight: '800', letterSpacing: -1 },
  per: { color: colors.textSecondary, fontSize: 14, marginBottom: 8 },
  featRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginVertical: 6 },
  featText: { color: colors.textPrimary, fontSize: 14 },
  cta: { marginTop: spacing.md, backgroundColor: colors.surfaceElev, paddingVertical: 14, borderRadius: radii.full, alignItems: 'center' },
  ctaPrimary: { backgroundColor: colors.primary },
  ctaActive: { backgroundColor: 'transparent', borderWidth: 1, borderColor: colors.border },
  ctaText: { color: colors.textPrimary, fontWeight: '700' },
  note: { color: colors.textTertiary, fontSize: 11, textAlign: 'center', marginTop: spacing.lg, fontStyle: 'italic' },
});
