import { StyleSheet, Text, View } from 'react-native';

import { t } from '@/i18n';

import { colors, radius, space } from './theme';

const TONES: Record<string, [background: string, text: string]> = {
  pending_payment: [colors.warningSoft, colors.warning],
  confirmed: [colors.successSoft, colors.success],
  completed: [colors.disabled, colors.muted],
  cancelled: [colors.dangerSoft, colors.danger],
  expired: [colors.disabled, colors.muted],
  no_show: [colors.dangerSoft, colors.danger],
};

/** Booking status as a labelled pill; unknown statuses are shown as-is. */
export function StatusBadge({ status }: { status: string }) {
  const [background, text] = TONES[status] ?? [colors.disabled, colors.muted];
  return (
    <View style={[styles.badge, { backgroundColor: background }]}>
      <Text style={[styles.text, { color: text }]}>{t.status[status] ?? status}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    alignSelf: 'flex-start',
    borderRadius: radius.pill,
    paddingHorizontal: space.md,
    paddingVertical: space.xs,
  },
  text: { fontSize: 13, fontWeight: '600' },
});
