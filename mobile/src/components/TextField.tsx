/**
 * Labelled text input with inline error text.
 *
 * The error slot matters for spec AC-03: the validation message has to identify
 * the offending field, not just appear somewhere on the screen.
 *
 * Border per DESIGN.md "text-input": the decorative hairline (`color.border`)
 * is too faint to meet WCAG 1.4.11's >=3:1 edge-contrast floor on an
 * interactive field, so this uses `color.borderInteractive` (ink-muted) instead.
 */
import { useState } from 'react';
import { StyleSheet, Text, TextInput, View, type TextInputProps } from 'react-native';

import { ns, nsFont } from '../theme/nullscapes';
import { color, font, radius, space } from '../theme/tokens';

type Props = TextInputProps & {
  label: string;
  /** Message shown under the field. Presence also turns the border red. */
  error?: string | null;
  /** testID for the error text, so a selector can assert the message location. */
  errorTestID?: string;
  hint?: string;
  /** 'cash-carry' (default): every screen outside the Tabs group, and any
   * Tabs screen not yet reskinned. 'nullscapes': the dark glass-card
   * treatment, for screens already on the Nullscapes visual system. */
  variant?: 'cash-carry' | 'nullscapes';
};

export function TextField({
  label,
  error,
  errorTestID,
  hint,
  style,
  onFocus,
  onBlur,
  variant = 'cash-carry',
  ...inputProps
}: Props) {
  const [focused, setFocused] = useState(false);
  const isNullscapes = variant === 'nullscapes';

  return (
    <View style={styles.container}>
      <Text style={isNullscapes ? styles.labelNullscapes : styles.label}>{label}</Text>
      <TextInput
        style={[
          isNullscapes ? styles.inputNullscapes : styles.input,
          focused ? (isNullscapes ? styles.inputFocusedNullscapes : styles.inputFocused) : null,
          error ? (isNullscapes ? styles.inputErrorNullscapes : styles.inputError) : null,
          style,
        ]}
        placeholderTextColor={isNullscapes ? ns.mutedFaint : color.textMuted}
        accessibilityLabel={label}
        {...inputProps}
        onFocus={(e) => {
          setFocused(true);
          onFocus?.(e);
        }}
        onBlur={(e) => {
          setFocused(false);
          onBlur?.(e);
        }}
      />
      {error ? (
        <Text testID={errorTestID} style={isNullscapes ? styles.errorNullscapes : styles.error}>
          {error}
        </Text>
      ) : hint ? (
        <Text style={isNullscapes ? styles.hintNullscapes : styles.hint}>{hint}</Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { gap: space.xs },
  label: { fontFamily: font.family.bodyMedium, fontSize: font.size.sm, color: color.text },
  labelNullscapes: { fontFamily: nsFont.medium, fontSize: 13, color: ns.muted, marginBottom: 2 },
  input: {
    borderWidth: 1,
    borderColor: color.borderInteractive,
    backgroundColor: color.surface,
    padding: space.md,
    borderRadius: radius.md,
    fontFamily: font.family.body,
    fontSize: font.size.lg,
    color: color.text,
  },
  // Lost its padding/border entirely when this variant was split out of
  // `input` — the box only grew to the font's own line-height, so fields
  // rendered as thin, edge-to-edge bars with no room to read back what was
  // typed. `minHeight` keeps every field a consistent, comfortably tappable
  // size regardless of platform font-metrics rounding.
  inputNullscapes: {
    borderWidth: 1,
    borderColor: ns.hairline,
    backgroundColor: ns.card,
    borderRadius: 10,
    paddingHorizontal: space.lg,
    paddingVertical: 14,
    minHeight: 52,
    fontFamily: nsFont.regular,
    fontSize: 16,
    color: ns.ink,
  },
  inputFocused: { borderWidth: 2, borderColor: color.primary },
  inputFocusedNullscapes: { borderWidth: 1, borderColor: ns.mint },
  inputError: { borderWidth: 1, borderColor: color.error.accent },
  inputErrorNullscapes: { borderWidth: 1, borderColor: ns.danger },
  error: { fontSize: font.size.sm, color: color.error.fg, fontWeight: font.weight.medium },
  errorNullscapes: { fontSize: 13, color: ns.danger, fontFamily: nsFont.medium },
  hint: { fontSize: font.size.sm, color: color.textMuted },
  hintNullscapes: { fontSize: 13, color: ns.mutedFaint, fontFamily: nsFont.regular, marginTop: 2 },
});
