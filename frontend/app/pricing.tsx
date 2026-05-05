import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Alert, Platform, Linking } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { Feather } from '@expo/vector-icons';
import * as WebBrowser from 'expo-web-browser';
import { colors, spacing, radii } from '../src/theme';
import { api } from '../src/api';
import { useAuth } from '../src/AuthContext';
import { useEffect, useState } from 'react';

type Cycle = 'monthly' | 'annual';

const PLANS: Array<{
  key: 'free' | 'pro' | 'coach';
  name: string;
  monthly: string;
  annual: string;
  annualTotal: string;
  save: string | null;
  highlight?: boolean;
  features: string[];
  cta: string;
}> = [
  { key: 'free', name: 'Free', monthly: '$0', annual: '$0', annualTotal: '$0', save: null, features: ['1 active goal', 'Basic AI plan', 'Manual tracking', 'Basic reminders'], cta: 'Current' },
  { key: 'pro', name: 'Pro', monthly: '$12', annual: '$9', annualTotal: '$108/yr', save: 'Save $36', highlight: true, features: ['Up to 5 goals', 'AI goal breakdown', 'Smart reminders', 'Calendar integration', 'Weekly AI review'], cta: 'Upgrade to Pro' },
  { key: 'coach', name: 'Coach', monthly: '$29', annual: '$21', annualTotal: '$252/yr', save: 'Save $96', features: ['Unlimited goals', 'Daily AI coaching', 'Advanced insights', 'Accountability mode', 'Priority automation'], cta: 'Upgrade to Coach' },
];

const BACKEND_BASE = process.env.EXPO_PUBLIC_BACKEND_URL || '';

export default function Pricing() {
  const router = useRouter();
  const params = useLocalSearchParams<{ session_id?: string }>();
  const { user, refreshUser } = useAuth();
  const [busy, setBusy] = useState<string | null>(null);
  const [cycle, setCycle] = useState<Cycle>('annual');
  const current = user?.plan || 'free';

  // If returning from Stripe with session_id (web flow), poll status here.
  useEffect(() => {
    if (!params?.session_id) return;
    let cancelled = false;
    let attempts = 0;
    const poll = async () => {
      while (!cancelled && attempts < 8) {
        attempts += 1;
        try {
          const { data } = await api.get(`/checkout/status/${params.session_id}`);
          if (data.payment_status === 'paid') {
            await refreshUser();
            Alert.alert('Payment confirmed', `Welcome to ${(data.plan || '').toUpperCase()} (${data.billing})!`);
            return;
          }
          if (data.status === 'expired') {
            Alert.alert('Session expired', 'Your checkout session expired. Please try again.');
            return;
          }
        } catch {}
        await new Promise(r => setTimeout(r, 2000));
      }
    };
    poll();
    return () => { cancelled = true; };
  }, [params?.session_id]);

  function getOriginUrl(): string {
    if (Platform.OS === 'web' && typeof window !== 'undefined') return window.location.origin;
    return BACKEND_BASE; // mobile uses preview URL as origin so success returns to web preview
  }

  async function startCheckout(plan: 'pro' | 'coach') {
    if (plan === current) return;
    setBusy(plan);
    try {
      const package_id = `${plan}_${cycle}`;
      const { data } = await api.post('/checkout/session', { package_id, origin_url: getOriginUrl() });
      const checkoutUrl: string = data.url;
      const sessionId: string = data.session_id;

      if (Platform.OS === 'web' && typeof window !== 'undefined') {
        window.location.href = checkoutUrl;
        return;
      }

      // Native: open Stripe Checkout in in-app browser
      const result = await WebBrowser.openAuthSessionAsync(checkoutUrl, `${BACKEND_BASE}/payment/success`);
      // Regardless of how the user returns, navigate to success screen and let it poll.
      router.push({ pathname: '/payment/success', params: { session_id: sessionId } });
    } catch (e: any) {
      const d = e?.response?.data?.detail;
      Alert.alert('Checkout failed', typeof d === 'string' ? d : 'Could not start checkout.');
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

        <View style={styles.toggleWrap}>
          <TouchableOpacity testID="pricing-toggle-monthly" style={[styles.toggleSeg, cycle === 'monthly' && styles.toggleSegActive]} onPress={() => setCycle('monthly')}>
            <Text style={[styles.toggleText, cycle === 'monthly' && styles.toggleTextActive]}>Monthly</Text>
          </TouchableOpacity>
          <TouchableOpacity testID="pricing-toggle-annual" style={[styles.toggleSeg, cycle === 'annual' && styles.toggleSegActive]} onPress={() => setCycle('annual')}>
            <Text style={[styles.toggleText, cycle === 'annual' && styles.toggleTextActive]}>Annual</Text>
            <View style={styles.saveBadge}><Text style={styles.saveBadgeText}>-25%</Text></View>
          </TouchableOpacity>
        </View>

        {PLANS.map(p => {
          const active = current === p.key;
          const price = cycle === 'annual' ? p.annual : p.monthly;
          return (
            <View key={p.key} style={[styles.card, p.highlight && styles.cardHighlight, active && styles.cardActive]} testID={`plan-card-${p.key}`}>
              {p.highlight && <View style={styles.popular}><Text style={styles.popularText}>MOST POPULAR</Text></View>}
              <Text style={styles.planName}>{p.name}</Text>
              <View style={styles.priceRow}>
                <Text style={styles.price}>{price}</Text>
                {p.monthly !== '$0' && <Text style={styles.per}>/month</Text>}
              </View>
              {cycle === 'annual' && p.save ? (
                <View style={styles.saveRow}>
                  <Text style={styles.saveTxt}>{p.save}</Text>
                  <Text style={styles.saveSub}>• Billed {p.annualTotal}</Text>
                </View>
              ) : null}
              {p.features.map((f, i) => (
                <View key={i} style={styles.featRow}>
                  <Feather name="check" size={15} color={colors.primary} />
                  <Text style={styles.featText}>{f}</Text>
                </View>
              ))}
              <TouchableOpacity
                disabled={active || busy !== null || p.key === 'free'}
                style={[styles.cta, active && styles.ctaActive, p.highlight && !active && styles.ctaPrimary]}
                onPress={() => p.key !== 'free' && startCheckout(p.key)}
                testID={`plan-cta-${p.key}`}
              >
                <Text style={[styles.ctaText, p.highlight && !active && { color: '#fff' }, active && { color: colors.textSecondary }]}>
                  {active ? 'Current plan' : busy === p.key ? 'Starting checkout…' : p.cta}
                </Text>
              </TouchableOpacity>
            </View>
          );
        })}

        <Text style={styles.note}>Secured by Stripe · Test mode</Text>
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
  toggleWrap: { flexDirection: 'row', backgroundColor: colors.surfaceElev, borderRadius: radii.full, padding: 4, marginBottom: spacing.lg, borderWidth: 1, borderColor: colors.border },
  toggleSeg: { flex: 1, paddingVertical: 10, borderRadius: radii.full, alignItems: 'center', justifyContent: 'center', flexDirection: 'row', gap: 6 },
  toggleSegActive: { backgroundColor: colors.primary },
  toggleText: { color: colors.textSecondary, fontWeight: '700', fontSize: 14 },
  toggleTextActive: { color: '#fff' },
  saveBadge: { backgroundColor: colors.secondary, paddingVertical: 2, paddingHorizontal: 6, borderRadius: radii.sm },
  saveBadgeText: { color: colors.bg, fontSize: 10, fontWeight: '800' },
  card: { backgroundColor: colors.surface, borderRadius: radii.lg, padding: spacing.lg, marginBottom: spacing.md, borderWidth: 1, borderColor: colors.border },
  cardHighlight: { borderColor: colors.primary, shadowColor: colors.primary, shadowOpacity: 0.3, shadowRadius: 20, shadowOffset: { width: 0, height: 4 } },
  cardActive: { borderColor: colors.success },
  popular: { position: 'absolute', top: -12, right: 16, backgroundColor: colors.primary, paddingVertical: 4, paddingHorizontal: 10, borderRadius: radii.full },
  popularText: { color: '#fff', fontSize: 10, fontWeight: '800', letterSpacing: 1.5 },
  planName: { color: colors.textPrimary, fontSize: 20, fontWeight: '800' },
  priceRow: { flexDirection: 'row', alignItems: 'flex-end', gap: 4, marginVertical: spacing.sm },
  price: { color: colors.textPrimary, fontSize: 38, fontWeight: '800', letterSpacing: -1 },
  per: { color: colors.textSecondary, fontSize: 14, marginBottom: 8 },
  saveRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: spacing.sm },
  saveTxt: { color: colors.success, fontSize: 12, fontWeight: '800', letterSpacing: 0.5 },
  saveSub: { color: colors.textTertiary, fontSize: 12 },
  featRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginVertical: 6 },
  featText: { color: colors.textPrimary, fontSize: 14 },
  cta: { marginTop: spacing.md, backgroundColor: colors.surfaceElev, paddingVertical: 14, borderRadius: radii.full, alignItems: 'center' },
  ctaPrimary: { backgroundColor: colors.primary },
  ctaActive: { backgroundColor: 'transparent', borderWidth: 1, borderColor: colors.border },
  ctaText: { color: colors.textPrimary, fontWeight: '700' },
  note: { color: colors.textTertiary, fontSize: 11, textAlign: 'center', marginTop: spacing.lg, fontStyle: 'italic' },
});
