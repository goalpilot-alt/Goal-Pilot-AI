import { Stack, useRouter, useSegments } from 'expo-router';
import { AuthProvider, useAuth } from '../src/AuthContext';
import { useEffect } from 'react';
import { View, ActivityIndicator, StyleSheet } from 'react-native';
import { colors } from '../src/theme';
import { StatusBar } from 'expo-status-bar';

function RootNav() {
  const { user, loading } = useAuth();
  const segments = useSegments();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    const inAuthGroup = segments[0] === '(tabs)' || segments[0] === 'goal';
    if (!user && inAuthGroup) {
      router.replace('/');
    } else if (user && (segments[0] === 'login' || segments[0] === 'register' || segments.length === 0 || segments[0] === undefined)) {
      router.replace('/(tabs)/dashboard');
    }
  }, [user, loading, segments]);

  if (loading) {
    return (
      <View style={styles.loader}>
        <ActivityIndicator color={colors.primary} size="large" />
      </View>
    );
  }

  return (
    <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.bg } }}>
      <Stack.Screen name="index" />
      <Stack.Screen name="login" />
      <Stack.Screen name="register" />
      <Stack.Screen name="(tabs)" />
      <Stack.Screen name="goal/new" options={{ presentation: 'modal' }} />
      <Stack.Screen name="goal/[id]" />
      <Stack.Screen name="pricing" options={{ presentation: 'modal' }} />
      <Stack.Screen name="payment/success" />
    </Stack>
  );
}

export default function RootLayout() {
  return (
    <AuthProvider>
      <StatusBar style="light" />
      <RootNav />
    </AuthProvider>
  );
}

const styles = StyleSheet.create({
  loader: { flex: 1, backgroundColor: colors.bg, alignItems: 'center', justifyContent: 'center' },
});
