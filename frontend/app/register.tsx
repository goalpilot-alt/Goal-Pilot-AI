import { View, Text, StyleSheet, TextInput, TouchableOpacity, KeyboardAvoidingView, Platform, ScrollView } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter, Link } from 'expo-router';
import { useState } from 'react';
import { Feather } from '@expo/vector-icons';
import { colors, spacing, radii } from '../src/theme';
import { useAuth } from '../src/AuthContext';
import { useI18n } from '../src/i18n/I18nProvider';

export default function Register() {
  const router = useRouter();
  const { register } = useAuth();
  const { t } = useI18n();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState('');

  async function onSubmit() {
    setErr('');
    if (!name || !email || !password) return setErr(t('fill_all_fields'));
    if (password.length < 6) return setErr(t('pw_too_short'));
    setLoading(true);
    try {
      await register(email.trim(), password, name.trim());
      router.replace('/(tabs)/dashboard');
    } catch (e: any) {
      const d = e?.response?.data?.detail;
      setErr(typeof d === 'string' ? d : t('signup_failed'));
    } finally { setLoading(false); }
  }

  return (
    <SafeAreaView style={styles.root} edges={['top', 'bottom']}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          <TouchableOpacity onPress={() => router.back()} style={styles.back} testID="register-back-btn">
            <Feather name="arrow-left" size={22} color={colors.textPrimary} />
          </TouchableOpacity>
          <Text style={styles.title}>{t('create_account')}</Text>
          <Text style={styles.subtitle}>{t('register_subtitle')}</Text>

          <View style={styles.field}>
            <Text style={styles.label}>{t('your_name')}</Text>
            <TextInput testID="register-name-input" value={name} onChangeText={setName} placeholder="Jordan Chen" placeholderTextColor={colors.textTertiary} style={styles.input} />
          </View>
          <View style={styles.field}>
            <Text style={styles.label}>{t('email')}</Text>
            <TextInput testID="register-email-input" value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" placeholder="you@goalpilot.ai" placeholderTextColor={colors.textTertiary} style={styles.input} />
          </View>
          <View style={styles.field}>
            <Text style={styles.label}>{t('password')}</Text>
            <TextInput testID="register-password-input" value={password} onChangeText={setPassword} secureTextEntry placeholder={t('pw_min_chars')} placeholderTextColor={colors.textTertiary} style={styles.input} />
          </View>

          {err ? <Text style={styles.err} testID="register-error">{err}</Text> : null}

          <TouchableOpacity testID="register-submit-btn" disabled={loading} style={[styles.btn, loading && { opacity: 0.6 }]} onPress={onSubmit}>
            <Text style={styles.btnText}>{loading ? t('creating_account') : t('create_account')}</Text>
          </TouchableOpacity>

          <View style={styles.footer}>
            <Text style={styles.footerTxt}>{t('have_account_q')}</Text>
            <Link href="/login" asChild>
              <TouchableOpacity testID="register-go-login-btn"><Text style={styles.link}>{t('log_in')}</Text></TouchableOpacity>
            </Link>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  scroll: { padding: spacing.lg, paddingTop: spacing.md },
  back: { width: 40, height: 40, borderRadius: 20, backgroundColor: colors.surface, alignItems: 'center', justifyContent: 'center', marginBottom: spacing.lg },
  title: { color: colors.textPrimary, fontSize: 32, fontWeight: '800', letterSpacing: -0.5 },
  subtitle: { color: colors.textSecondary, fontSize: 15, marginTop: spacing.xs, marginBottom: spacing.xl },
  field: { marginBottom: spacing.md },
  label: { color: colors.textSecondary, fontSize: 12, fontWeight: '600', marginBottom: 6, letterSpacing: 0.5, textTransform: 'uppercase' },
  input: { backgroundColor: colors.surfaceElev, color: colors.textPrimary, borderRadius: radii.md, paddingHorizontal: 16, paddingVertical: 14, fontSize: 16, borderWidth: 1, borderColor: colors.border },
  btn: { backgroundColor: colors.primary, paddingVertical: 16, borderRadius: radii.full, alignItems: 'center', marginTop: spacing.md, shadowColor: colors.primary, shadowOpacity: 0.5, shadowRadius: 14, shadowOffset: { width: 0, height: 4 } },
  btnText: { color: '#fff', fontWeight: '700', fontSize: 16 },
  err: { color: colors.error, marginTop: spacing.xs },
  footer: { flexDirection: 'row', justifyContent: 'center', marginTop: spacing.xl },
  footerTxt: { color: colors.textSecondary },
  link: { color: colors.primary, fontWeight: '700' },
});
