import { View, Text, StyleSheet, ActivityIndicator, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { Feather } from '@expo/vector-icons';
import { colors, spacing, radii } from '../../src/theme';
import { api } from '../../src/api';
import { useAuth } from '../../src/AuthContext';

type Status = 'polling' | 'paid' | 'expired' | 'error' | 'pending';

export default function PaymentSuccess() {
  const router = useRouter();
  const { session_id } = useLocalSearchParams<{ session_id?: string }>();
  const { refreshUser } = useAuth();
  const [status, setStatus] = useState<Status>('polling');
  const [info, setInfo] = useState<{ amount?: number; plan?: string; billing?: string }>({});
  const attempts = useRef(0);
  const cancelled = useRef(false);

  useEffect(() => {
    if (!session_id) { setStatus('error'); return; }
    const poll = async () => {
      const max = 8;
      while (!cancelled.current && attempts.current < max) {
        attempts.current += 1;
        try {
          const { data } = await api.get(`/checkout/status/${session_id}`);
          setInfo({ amount: data.amount_total, plan: data.plan, billing: data.billing });
          if (data.payment_status === 'paid') {
            setStatus('paid');
            await refreshUser();
            return;
          }
          if (data.status === 'expired') { setStatus('expired'); return; }
          setStatus('pending');
        } catch {
          // keep polling
        }
        await new Promise(r => setTimeout(r, 2000));
      }
      if (!cancelled.current) setStatus('error');
    };
    poll();
    return () => { cancelled.current = true; };
  }, [session_id]);

  return (
    <SafeAreaView style={styles.root} edges={['top', 'bottom']}>
      <View style={styles.container}>
        {status === 'polling' || status === 'pending' ? (
          <>
            <ActivityIndicator color={colors.primary} size="large" />
            <Text style={styles.title}>Confirming your payment…</Text>
            <Text style={styles.sub}>This usually takes a few seconds.</Text>
          </>
        ) : status === 'paid' ? (
          <>
            <View style={styles.successIcon}><Feather name="check" size={36} color="#fff" /></View>
            <Text style={styles.title} testID="payment-success-title">You&apos;re upgraded!</Text>
            <Text style={styles.sub}>
              Welcome to {(info.plan || '').toUpperCase()} ({info.billing}). Time to crush your goals.
            </Text>
            <TouchableOpacity testID="payment-success-cta" style={styles.cta} onPress={() => router.replace('/(tabs)/dashboard')}>
              <Text style={styles.ctaText}>Go to Dashboard</Text>
              <Feather name="arrow-right" size={18} color="#fff" />
            </TouchableOpacity>
          </>
        ) : (
          <>
            <View style={styles.errIcon}><Feather name="alert-triangle" size={32} color={colors.warning} /></View>
            <Text style={styles.title}>Payment {status === 'expired' ? 'expired' : 'check failed'}</Text>
            <Text style={styles.sub}>
              {status === 'expired' ? 'Your checkout session expired. Please try again.' : 'We couldn\u2019t confirm your payment. If you were charged, the upgrade will reflect shortly.'}
            </Text>
            <TouchableOpacity style={styles.cta} onPress={() => router.replace('/pricing')}>
              <Text style={styles.ctaText}>Back to pricing</Text>
            </TouchableOpacity>
          </>
        )}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  container: { flex: 1, padding: spacing.xl, alignItems: 'center', justifyContent: 'center', gap: spacing.md },
  successIcon: { width: 80, height: 80, borderRadius: 40, backgroundColor: colors.success, alignItems: 'center', justifyContent: 'center', marginBottom: spacing.sm },
  errIcon: { width: 80, height: 80, borderRadius: 40, backgroundColor: 'rgba(245,158,11,0.15)', alignItems: 'center', justifyContent: 'center', marginBottom: spacing.sm },
  title: { color: colors.textPrimary, fontSize: 26, fontWeight: '800', textAlign: 'center', letterSpacing: -0.5 },
  sub: { color: colors.textSecondary, fontSize: 15, textAlign: 'center', lineHeight: 22, maxWidth: 320 },
  cta: { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: colors.primary, paddingVertical: 14, paddingHorizontal: 28, borderRadius: radii.full, marginTop: spacing.md, shadowColor: colors.primary, shadowOpacity: 0.5, shadowRadius: 12 },
  ctaText: { color: '#fff', fontWeight: '700', fontSize: 15 },
});
