import { View, Text, StyleSheet, ActivityIndicator, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { Feather } from '@expo/vector-icons';
import { colors, spacing, radii, shadows } from '../../src/theme';
import { api } from '../../src/api';
import { useAuth } from '../../src/AuthContext';
import { useI18n } from '../../src/i18n/I18nProvider';

type Status = 'polling' | 'paid' | 'expired' | 'error' | 'pending';

export default function PaymentSuccess() {
  const router = useRouter();
  const { t } = useI18n();
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
        } catch {}
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
            <Text style={styles.title}>{t('confirming_payment')}</Text>
            <Text style={styles.sub}>{t('takes_seconds')}</Text>
          </>
        ) : status === 'paid' ? (
          <>
            <View style={styles.successIcon}><Feather name="check" size={36} color="#fff" /></View>
            <Text style={styles.title} testID="payment-success-title">{t('youre_upgraded')}</Text>
            <Text style={styles.sub}>{t('welcome_to_plan_long', { plan: (info.plan || '').toUpperCase(), billing: info.billing || '' })}</Text>
            <TouchableOpacity testID="payment-success-cta" style={styles.cta} onPress={() => router.replace('/(tabs)/dashboard')}>
              <Text style={styles.ctaText}>{t('go_to_dashboard')}</Text>
              <Feather name="arrow-right" size={18} color="#fff" />
            </TouchableOpacity>
          </>
        ) : (
          <>
            <View style={styles.errIcon}><Feather name="alert-triangle" size={32} color={colors.warning} /></View>
            <Text style={styles.title}>{status === 'expired' ? t('payment_expired') : t('payment_check_failed')}</Text>
            <Text style={styles.sub}>{status === 'expired' ? t('session_expired_msg') : ''}</Text>
            <TouchableOpacity style={styles.cta} onPress={() => router.replace('/pricing')}>
              <Text style={styles.ctaText}>{t('back_to_pricing')}</Text>
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
  cta: { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: colors.primary, paddingVertical: 14, paddingHorizontal: 28, borderRadius: radii.full, marginTop: spacing.md, boxShadow: shadows.primaryMd },
  ctaText: { color: '#fff', fontWeight: '700', fontSize: 15 },
});
