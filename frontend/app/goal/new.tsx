import { View, Text, StyleSheet, ScrollView, TextInput, TouchableOpacity, KeyboardAvoidingView, Platform, ActivityIndicator, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Feather } from '@expo/vector-icons';
import { colors, spacing, radii } from '../../src/theme';
import { api } from '../../src/api';

const LEVELS = [
  { key: 'beginner', label: 'Beginner', desc: 'Just starting out' },
  { key: 'intermediate', label: 'Intermediate', desc: 'Some experience' },
  { key: 'advanced', label: 'Advanced', desc: 'Pushing further' },
];

const HOURS = [3, 5, 10, 15, 20];

export default function NewGoal() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [title, setTitle] = useState('');
  const [deadline, setDeadline] = useState('');
  const [motivation, setMotivation] = useState('');
  const [level, setLevel] = useState('beginner');
  const [hours, setHours] = useState(5);
  const [loading, setLoading] = useState(false);

  function next() { setStep(s => Math.min(3, s + 1)); }
  function prev() { if (step === 0) router.back(); else setStep(s => s - 1); }

  const canNext =
    (step === 0 && title.trim().length >= 3) ||
    (step === 1 && /^\d{4}-\d{2}-\d{2}$/.test(deadline)) ||
    (step === 2 && motivation.trim().length >= 5) ||
    step === 3;

  async function submit() {
    setLoading(true);
    try {
      const { data } = await api.post('/goals', {
        title: title.trim(),
        deadline,
        motivation: motivation.trim(),
        current_level: level,
        hours_per_week: hours,
      });
      router.replace(`/goal/${data.id}`);
    } catch (e: any) {
      const d = e?.response?.data?.detail;
      Alert.alert('Oops', typeof d === 'string' ? d : 'Could not create goal');
    } finally { setLoading(false); }
  }

  return (
    <SafeAreaView style={styles.root} edges={['top', 'bottom']}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1 }}>
        <View style={styles.topBar}>
          <TouchableOpacity onPress={prev} style={styles.backBtn} testID="new-goal-back">
            <Feather name="arrow-left" size={22} color={colors.textPrimary} />
          </TouchableOpacity>
          <View style={styles.progress}>
            {[0, 1, 2, 3].map(i => (
              <View key={i} style={[styles.progressSeg, i <= step && styles.progressSegActive]} />
            ))}
          </View>
        </View>

        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          {step === 0 && (
            <>
              <Text style={styles.eyebrow}>STEP 1 OF 4</Text>
              <Text style={styles.qTitle}>What&apos;s your goal?</Text>
              <Text style={styles.qSub}>Be specific. Our AI plans better with clarity.</Text>
              <TextInput
                testID="new-goal-title-input"
                value={title}
                onChangeText={setTitle}
                placeholder="e.g. Run a half marathon by June"
                placeholderTextColor={colors.textTertiary}
                style={styles.input}
                multiline
              />
            </>
          )}
          {step === 1 && (
            <>
              <Text style={styles.eyebrow}>STEP 2 OF 4</Text>
              <Text style={styles.qTitle}>By when?</Text>
              <Text style={styles.qSub}>Your target completion date.</Text>
              <TextInput
                testID="new-goal-deadline-input"
                value={deadline}
                onChangeText={setDeadline}
                placeholder="YYYY-MM-DD"
                placeholderTextColor={colors.textTertiary}
                style={styles.input}
              />
              <Text style={styles.hint}>Format: 2026-06-15</Text>
            </>
          )}
          {step === 2 && (
            <>
              <Text style={styles.eyebrow}>STEP 3 OF 4</Text>
              <Text style={styles.qTitle}>Why does this matter?</Text>
              <Text style={styles.qSub}>Your motivation keeps you accountable.</Text>
              <TextInput
                testID="new-goal-motivation-input"
                value={motivation}
                onChangeText={setMotivation}
                placeholder="I want to prove to myself…"
                placeholderTextColor={colors.textTertiary}
                style={[styles.input, { minHeight: 120 }]}
                multiline
              />
            </>
          )}
          {step === 3 && (
            <>
              <Text style={styles.eyebrow}>STEP 4 OF 4</Text>
              <Text style={styles.qTitle}>Where are you now?</Text>
              <Text style={styles.qSub}>Current level & weekly time commitment.</Text>

              <Text style={styles.label}>Current level</Text>
              {LEVELS.map(l => (
                <TouchableOpacity
                  key={l.key}
                  testID={`level-${l.key}`}
                  style={[styles.chip, level === l.key && styles.chipActive]}
                  onPress={() => setLevel(l.key)}
                >
                  <View style={{ flex: 1 }}>
                    <Text style={[styles.chipTitle, level === l.key && { color: colors.primary }]}>{l.label}</Text>
                    <Text style={styles.chipDesc}>{l.desc}</Text>
                  </View>
                  {level === l.key ? <Feather name="check-circle" size={18} color={colors.primary} /> : null}
                </TouchableOpacity>
              ))}

              <Text style={[styles.label, { marginTop: spacing.md }]}>Hours per week: {hours}</Text>
              <View style={styles.hoursRow}>
                {HOURS.map(h => (
                  <TouchableOpacity
                    key={h}
                    testID={`hours-${h}`}
                    style={[styles.hourChip, hours === h && styles.hourChipActive]}
                    onPress={() => setHours(h)}
                  >
                    <Text style={[styles.hourText, hours === h && { color: '#fff' }]}>{h}h</Text>
                  </TouchableOpacity>
                ))}
              </View>
            </>
          )}
        </ScrollView>

        <View style={styles.bottomBar}>
          {step < 3 ? (
            <TouchableOpacity
              disabled={!canNext}
              style={[styles.nextBtn, !canNext && { opacity: 0.5 }]}
              onPress={next}
              testID="new-goal-next-btn"
            >
              <Text style={styles.nextText}>Continue</Text>
              <Feather name="arrow-right" size={18} color="#fff" />
            </TouchableOpacity>
          ) : (
            <TouchableOpacity
              disabled={loading}
              style={[styles.nextBtn, loading && { opacity: 0.6 }]}
              onPress={submit}
              testID="new-goal-submit-btn"
            >
              {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.nextText}>Generate AI Plan</Text>}
              {!loading && <Feather name="zap" size={18} color="#fff" />}
            </TouchableOpacity>
          )}
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  topBar: { flexDirection: 'row', alignItems: 'center', gap: spacing.md, paddingHorizontal: spacing.lg, paddingTop: spacing.md },
  backBtn: { width: 40, height: 40, borderRadius: 20, backgroundColor: colors.surface, alignItems: 'center', justifyContent: 'center' },
  progress: { flex: 1, flexDirection: 'row', gap: 6 },
  progressSeg: { flex: 1, height: 4, borderRadius: 2, backgroundColor: colors.surfaceElev },
  progressSegActive: { backgroundColor: colors.primary },
  scroll: { padding: spacing.lg, paddingTop: spacing.xl },
  eyebrow: { color: colors.primary, fontSize: 11, fontWeight: '700', letterSpacing: 2 },
  qTitle: { color: colors.textPrimary, fontSize: 30, fontWeight: '800', letterSpacing: -0.5, marginTop: spacing.xs },
  qSub: { color: colors.textSecondary, fontSize: 15, marginTop: spacing.sm, marginBottom: spacing.lg },
  input: { backgroundColor: colors.surfaceElev, color: colors.textPrimary, borderRadius: radii.md, padding: 16, fontSize: 17, borderWidth: 1, borderColor: colors.border, minHeight: 60 },
  hint: { color: colors.textTertiary, fontSize: 12, marginTop: 6 },
  label: { color: colors.textSecondary, fontSize: 12, fontWeight: '700', letterSpacing: 1, textTransform: 'uppercase', marginBottom: spacing.sm, marginTop: spacing.sm },
  chip: { flexDirection: 'row', alignItems: 'center', padding: spacing.md, borderRadius: radii.md, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border, marginBottom: spacing.sm },
  chipActive: { borderColor: colors.primary, backgroundColor: 'rgba(255,94,0,0.08)' },
  chipTitle: { color: colors.textPrimary, fontSize: 15, fontWeight: '700' },
  chipDesc: { color: colors.textTertiary, fontSize: 12, marginTop: 2 },
  hoursRow: { flexDirection: 'row', gap: 8, flexWrap: 'wrap' },
  hourChip: { paddingVertical: 12, paddingHorizontal: 18, borderRadius: radii.full, backgroundColor: colors.surfaceElev, borderWidth: 1, borderColor: colors.border },
  hourChipActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  hourText: { color: colors.textPrimary, fontWeight: '700' },
  bottomBar: { padding: spacing.lg, borderTopWidth: 1, borderTopColor: colors.border },
  nextBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: spacing.sm, backgroundColor: colors.primary, paddingVertical: 16, borderRadius: radii.full, shadowColor: colors.primary, shadowOpacity: 0.5, shadowRadius: 14 },
  nextText: { color: '#fff', fontWeight: '700', fontSize: 16 },
});
