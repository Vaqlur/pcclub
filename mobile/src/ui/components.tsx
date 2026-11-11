import type { ReactNode } from 'react';
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  type TextInputProps,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { errorMessage, t } from '@/i18n';

import { radius, space, useTheme } from './theme';

/** Page frame: safe area on the sides and bottom (the stack header covers the top), scrolling. */
export function Screen({
  children,
  scroll = true,
  refreshing = false,
  onRefresh,
}: {
  children: ReactNode;
  scroll?: boolean;
  refreshing?: boolean;
  onRefresh?: () => void;
}) {
  const { colors } = useTheme();
  return (
    <SafeAreaView
      style={[styles.screen, { backgroundColor: colors.background }]}
      edges={['left', 'right', 'bottom']}
    >
      {scroll ? (
        <ScrollView
          contentContainerStyle={styles.content}
          keyboardShouldPersistTaps="handled"
          refreshControl={
            onRefresh ? (
              <RefreshControl
                refreshing={refreshing}
                onRefresh={onRefresh}
                tintColor={colors.primary}
                colors={[colors.primary]}
                progressBackgroundColor={colors.surface}
              />
            ) : undefined
          }
        >
          {children}
        </ScrollView>
      ) : (
        <View style={[styles.content, styles.fill]}>{children}</View>
      )}
    </SafeAreaView>
  );
}

type ButtonProps = {
  title: string;
  onPress: () => void;
  variant?: 'primary' | 'secondary' | 'danger' | 'link';
  disabled?: boolean;
  loading?: boolean;
  /** Spoken name when the title is only a symbol such as "+". */
  accessibilityLabel?: string;
};

export function Button({
  title,
  onPress,
  variant = 'primary',
  disabled,
  loading,
  accessibilityLabel,
}: ButtonProps) {
  const { colors } = useTheme();
  const inactive = disabled || loading;
  const textColor =
    inactive && variant !== 'link'
      ? colors.disabledText
      : variant === 'primary'
        ? colors.onPrimary
        : variant === 'danger'
          ? colors.danger
          : colors.primary;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel}
      accessibilityState={{ disabled: !!inactive, busy: !!loading }}
      disabled={inactive}
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        variant === 'primary' && {
          backgroundColor: pressed ? colors.primaryPressed : colors.primary,
        },
        variant === 'secondary' && [
          styles.buttonOutline,
          { borderColor: colors.primary, backgroundColor: colors.surface },
        ],
        variant === 'danger' && [
          styles.buttonOutline,
          { borderColor: colors.danger, backgroundColor: colors.surface },
        ],
        variant === 'link' && styles.buttonLink,
        inactive &&
          variant !== 'link' && {
            backgroundColor: colors.disabled,
            borderColor: colors.disabled,
          },
        pressed && variant !== 'primary' && { opacity: 0.6 },
      ]}
    >
      {loading ? (
        <ActivityIndicator color={variant === 'primary' ? colors.muted : colors.primary} />
      ) : (
        <Text style={[styles.buttonText, { color: textColor }]}>{title}</Text>
      )}
    </Pressable>
  );
}

type FieldProps = TextInputProps & { label: string; error?: string | null };

export function Field({ label, error, style, ...input }: FieldProps) {
  const { colors } = useTheme();
  return (
    <View style={styles.field}>
      <Text style={[styles.label, { color: colors.muted }]}>{label}</Text>
      <TextInput
        accessibilityLabel={label}
        placeholderTextColor={colors.disabledText}
        style={[
          styles.input,
          {
            borderColor: error ? colors.danger : colors.border,
            color: colors.text,
            backgroundColor: colors.surface,
          },
          style,
        ]}
        {...input}
      />
      {error ? <Text style={[styles.fieldError, { color: colors.danger }]}>{error}</Text> : null}
    </View>
  );
}

type NoticeProps = { tone?: 'error' | 'success' | 'warning' | 'info'; children: ReactNode };

export function Notice({ tone = 'error', children }: NoticeProps) {
  const { colors } = useTheme();
  const palette = {
    error: [colors.dangerSoft, colors.danger],
    success: [colors.successSoft, colors.success],
    warning: [colors.warningSoft, colors.warning],
    info: [colors.primarySoft, colors.primary],
  }[tone];
  return (
    <View
      accessibilityRole={tone === 'error' ? 'alert' : undefined}
      style={[styles.notice, { backgroundColor: palette[0] }]}
    >
      <Text style={[styles.noticeText, { color: palette[1] }]}>{children}</Text>
    </View>
  );
}

export function Card({ children, onPress }: { children: ReactNode; onPress?: () => void }) {
  const { colors } = useTheme();
  const cardStyle = [
    styles.card,
    { backgroundColor: colors.surface, borderColor: colors.border },
  ];
  if (!onPress) return <View style={cardStyle}>{children}</View>;
  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      style={({ pressed }) => [...cardStyle, pressed && { backgroundColor: colors.primarySoft }]}
    >
      {children}
    </Pressable>
  );
}

type ChipProps = {
  label: string;
  selected?: boolean;
  disabled?: boolean;
  onPress: () => void;
  sublabel?: string;
};

export function Chip({ label, sublabel, selected, disabled, onPress }: ChipProps) {
  const { colors } = useTheme();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected: !!selected, disabled: !!disabled }}
      disabled={disabled}
      onPress={onPress}
      style={[
        styles.chip,
        { borderColor: colors.border, backgroundColor: colors.surface },
        selected && { backgroundColor: colors.primary, borderColor: colors.primary },
        disabled && { backgroundColor: colors.disabled, borderColor: colors.disabled },
      ]}
    >
      <Text
        style={[
          styles.chipText,
          { color: colors.text },
          selected && { color: colors.onPrimary },
          disabled && { color: colors.disabledText },
        ]}
      >
        {label}
      </Text>
      {sublabel ? (
        <Text
          style={[
            styles.chipSub,
            { color: colors.muted },
            selected && { color: colors.onPrimary },
          ]}
        >
          {sublabel}
        </Text>
      ) : null}
    </Pressable>
  );
}

/** Loading / error / content switch for a screen's main request. */
export function Loadable<T>({
  state,
  children,
}: {
  state: { data: T | null; error: unknown; loading: boolean; reload: () => void };
  children: (data: T) => ReactNode;
}) {
  const { colors } = useTheme();
  if (state.data !== null) return <>{children(state.data)}</>;
  if (state.error) {
    return (
      <View style={styles.centered}>
        <Notice>{errorMessage(state.error)}</Notice>
        <Button title={t.common.retry} variant="secondary" onPress={state.reload} />
      </View>
    );
  }
  return (
    <View style={styles.centered}>
      <ActivityIndicator color={colors.primary} accessibilityLabel={t.common.loading} />
    </View>
  );
}

export function Row({ label, value }: { label: string; value: string }) {
  const { font } = useTheme();
  return (
    <View style={styles.row}>
      <Text style={font.small}>{label}</Text>
      <Text style={[font.body, styles.rowValue]}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  content: {
    padding: space.lg,
    gap: space.md,
    width: '100%',
    maxWidth: 560,
    alignSelf: 'center',
  },
  fill: { flex: 1 },
  button: {
    minHeight: 48,
    borderRadius: radius.md,
    paddingHorizontal: space.lg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  buttonOutline: { borderWidth: 1 },
  buttonLink: { minHeight: 40, paddingHorizontal: space.sm },
  buttonText: { fontSize: 16, fontWeight: '600' },
  field: { gap: space.xs },
  label: { fontSize: 14, fontWeight: '500' },
  input: {
    minHeight: 48,
    borderWidth: 1,
    borderRadius: radius.md,
    paddingHorizontal: space.md,
    fontSize: 17,
  },
  fieldError: { fontSize: 14 },
  notice: { borderRadius: radius.md, padding: space.md },
  noticeText: { fontSize: 15, lineHeight: 21 },
  card: {
    borderRadius: radius.md,
    borderWidth: 1,
    padding: space.lg,
    gap: space.xs,
  },
  chip: {
    minHeight: 40,
    minWidth: 64,
    paddingHorizontal: space.md,
    paddingVertical: space.sm,
    borderRadius: radius.sm,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  chipText: { fontSize: 15, fontWeight: '500' },
  chipSub: { fontSize: 12 },
  centered: { paddingVertical: space.xl, gap: space.md },
  row: { flexDirection: 'row', justifyContent: 'space-between', gap: space.md },
  rowValue: { flexShrink: 1, textAlign: 'right' },
});
