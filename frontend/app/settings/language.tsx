import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Feather } from '@expo/vector-icons';
import { colors, spacing, radii } from '../../src/theme';
import { useI18n } from '../../src/i18n/I18nProvider';
import type { LocaleCode } from '../../src/i18n';

export default function LanguageScreen() {
  const router = useRouter();
  const { locale, setLocale, supported, t } = useI18n();

  return (
    <SafeAreaView style={styles.root} edges={['top', 'bottom']}>
      <View style={styles.topRow}>
        <TouchableOpacity onPress={() => router.back()} style={styles.iconBtn} testID="lang-back-btn">
          <Feather name="x" size={22} color={colors.textPrimary} />
        </TouchableOpacity>
        <Text style={styles.title}>{t('language')}</Text>
        <View style={{ width: 40 }} />
      </View>

      <ScrollView contentContainerStyle={styles.scroll}>
        {supported.map((s) => {
          const active = s.code === locale;
          return (
            <TouchableOpacity
              key={s.code}
              testID={`lang-${s.code}`}
              activeOpacity={0.85}
              style={[styles.row, active && styles.rowActive]}
              onPress={async () => {
                if (!active) await setLocale(s.code as LocaleCode);
                router.back();
              }}
            >
              <View style={{ flex: 1 }}>
                <Text style={[styles.rowTitle, active && { color: colors.primary }]}>{s.label}</Text>
                <Text style={styles.rowSub}>{s.code}</Text>
              </View>
              {active ? <Feather name="check-circle" size={20} color={colors.primary} /> : null}
            </TouchableOpacity>
          );
        })}
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
  row: { flexDirection: 'row', alignItems: 'center', padding: spacing.md, borderRadius: radii.md, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, marginBottom: spacing.sm },
  rowActive: { borderColor: colors.primary, backgroundColor: 'rgba(255,94,0,0.08)' },
  rowTitle: { color: colors.textPrimary, fontSize: 16, fontWeight: '700' },
  rowSub: { color: colors.textTertiary, fontSize: 12, marginTop: 2 },
});
