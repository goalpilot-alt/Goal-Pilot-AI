import { View, Text, StyleSheet, TextInput, TouchableOpacity, KeyboardAvoidingView, Platform, ScrollView, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter, Link } from 'expo-router';
import { useState } from 'react';
import { Feather } from '@expo/vector-icons';
import { colors, spacing, radii } from '../src/theme';
import { useAuth } from '../src/AuthContext';

export default function Login() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState('');

  async function onSubmit() {
    setErr('');
    if (!email || !password) return setErr('Please fill all fields');
    setLoading(true);
    try {
      await login(email.trim(), password);
      router.replace('/(tabs)/dashboard');
    } catch (e: any) {
      const d = e?.response?.data?.detail;
      setErr(typeof d === 'string' ? d : 'Login failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <SafeAreaView style={styles.root} edges={['top', 'bottom']}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          <TouchableOpacity onPress={() => router.back()} style={styles.back} testID="login-back-btn">
            <Feather name="arrow-left" size={22} color={colors.textPrimary} />
          </TouchableOpacity>
          <Text style={styles.title}>Welcome back</Text>
          <Text style={styles.subtitle}>Log in to keep the momentum going.</Text>

          <View style={styles.field}>
            <Text style={styles.label}>Email</Text>
            <TextInput
              testID="login-email-input"
              value={email}
              onChangeText={setEmail}
              autoCapitalize="none"
              keyboardType="email-address"
              placeholder="you@goalpilot.ai"
              placeholderTextColor={colors.textTertiary}
              style={styles.input}
            />
          </View>

          <View style={styles.field}>
            <Text style={styles.label}>Password</Text>
            <TextInput
              testID="login-password-input"
              value={password}
              onChangeText={setPassword}
              secureTextEntry
              placeholder="••••••••"
              placeholderTextColor={colors.textTertiary}
              style={styles.input}
            />
          </View>

          {err ? <Text style={styles.err} testID="login-error">{err}</Text> : null}

          <TouchableOpacity testID="login-submit-btn" disabled={loading} style={[styles.btn, loading && { opacity: 0.6 }]} onPress={onSubmit}>
            <Text style={styles.btnText}>{loading ? 'Signing in…' : 'Log in'}</Text>
          </TouchableOpacity>

          <View style={styles.footer}>
            <Text style={styles.footerTxt}>New here? </Text>
            <Link href="/register" asChild>
              <TouchableOpacity testID="login-go-register-btn"><Text style={styles.link}>Create account</Text></TouchableOpacity>
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
