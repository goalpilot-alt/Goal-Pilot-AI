import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { Feather } from '@expo/vector-icons';
import { colors, spacing, radii } from '../../src/theme';
import { useI18n } from '../../src/i18n/I18nProvider';
import { PRIVACY, TERMS, REFUND } from '../../src/legal/policies';

const POLICIES: Record<string, { titleKey: string; body: string }> = {
  privacy: { titleKey: 'privacy_policy', body: PRIVACY },
  terms:   { titleKey: 'terms_of_service', body: TERMS },
  refund:  { titleKey: 'refund_policy',  body: REFUND },
};

export default function PolicyScreen() {
  const router = useRouter();
  const { t } = useI18n();
  const { kind } = useLocalSearchParams<{ kind?: string }>();
  const policy = POLICIES[kind || 'privacy'] || POLICIES.privacy;

  // Render a simple line-based formatter:
  //   **bold** -> bold text
  //   leading "**…**\nEffective: …" header gets emphasis automatically
  const lines = policy.body.split('\n');

  return (
    <SafeAreaView style={styles.root} edges={['top', 'bottom']}>
      <View style={styles.topRow}>
        <TouchableOpacity onPress={() => router.back()} style={styles.iconBtn} testID="policy-back-btn">
          <Feather name="x" size={22} color={colors.textPrimary} />
        </TouchableOpacity>
        <Text style={styles.title}>{t(policy.titleKey)}</Text>
        <View style={{ width: 40 }} />
      </View>

      <ScrollView contentContainerStyle={styles.scroll}>
        {lines.map((raw, i) => {
          const trimmed = raw.trim();
          if (!trimmed) return <View key={i} style={{ height: spacing.sm }} />;
          const isHeading = trimmed.startsWith('**') && trimmed.endsWith('**');
          if (isHeading) {
            const txt = trimmed.replace(/^\*\*/, '').replace(/\*\*$/, '');
            return <Text key={i} style={styles.heading}>{txt}</Text>;
          }
          // Render inline bold
          const parts = raw.split(/(\*\*[^*]+\*\*)/g);
          return (
            <Text key={i} style={styles.body}>
              {parts.map((p, j) => {
                if (p.startsWith('**') && p.endsWith('**')) {
                  return <Text key={j} style={{ fontWeight: '700', color: colors.textPrimary }}>{p.slice(2, -2)}</Text>;
                }
                return p;
              })}
            </Text>
          );
        })}
        <View style={{ height: 32 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  topRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: spacing.lg, paddingVertical: spacing.md },
  iconBtn: { width: 40, height: 40, borderRadius: 20, backgroundColor: colors.surface, alignItems: 'center', justifyContent: 'center' },
  title: { color: colors.textPrimary, fontSize: 18, fontWeight: '700' },
  scroll: { padding: spacing.lg },
  heading: { color: colors.primary, fontSize: 16, fontWeight: '800', marginTop: spacing.md, marginBottom: 4 },
  body: { color: colors.textSecondary, fontSize: 14, lineHeight: 22, marginBottom: 4 },
});
