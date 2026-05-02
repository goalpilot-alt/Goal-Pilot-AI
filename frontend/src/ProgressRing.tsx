import React from 'react';
import Svg, { Circle } from 'react-native-svg';
import { View, Text, StyleSheet } from 'react-native';
import { colors } from './theme';

type Props = { size?: number; stroke?: number; percent: number; label?: string };

export default function ProgressRing({ size = 140, stroke = 12, percent, label }: Props) {
  const radius = (size - stroke) / 2;
  const circ = 2 * Math.PI * radius;
  const clamped = Math.max(0, Math.min(100, percent));
  const offset = circ * (1 - clamped / 100);

  return (
    <View style={{ width: size, height: size, alignItems: 'center', justifyContent: 'center' }}>
      <Svg width={size} height={size}>
        <Circle cx={size / 2} cy={size / 2} r={radius} stroke={colors.surfaceElev} strokeWidth={stroke} fill="none" />
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={colors.primary}
          strokeWidth={stroke}
          strokeLinecap="round"
          fill="none"
          strokeDasharray={`${circ} ${circ}`}
          strokeDashoffset={offset}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </Svg>
      <View style={styles.center}>
        <Text style={styles.pct}>{clamped}%</Text>
        {label ? <Text style={styles.lbl}>{label}</Text> : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  center: { position: 'absolute', alignItems: 'center' },
  pct: { color: colors.textPrimary, fontSize: 32, fontWeight: '800' },
  lbl: { color: colors.textSecondary, fontSize: 12, marginTop: 2 },
});
