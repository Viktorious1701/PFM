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

import { color, font, radius, space } from '../theme/tokens';

type Props = TextInputProps & {
  label: string;
  /** Message shown under the field. Presence also turns the border red. */
  error?: string | null;
  /** testID for the error text, so a selector can assert the message location. */
  errorTestID?: string;
  hint?: string;
};

export function TextField({
  label,
  error,
  errorTestID,
  hint,
  style,
  onFocus,
  onBlur,
  ...inputProps
}: Props) {
  const [focused, setFocused] = useState(false);

  return (
    <View style={styles.container}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        style={[
          styles.input,
          focused ? styles.inputFocused : null,
          error ? styles.inputError : null,
          style,
        ]}
        placeholderTextColor={color.textMuted}
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
        <Text testID={errorTestID} style={styles.error}>
          {error}
        </Text>
      ) : hint ? (
        <Text style={styles.hint}>{hint}</Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { gap: space.xs },
  label: { fontFamily: font.family.bodyMedium, fontSize: font.size.sm, color: color.text },
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
  inputFocused: { borderWidth: 2, borderColor: color.primary },
  inputError: { borderWidth: 1, borderColor: color.error.accent },
  error: { fontSize: font.size.sm, color: color.error.fg, fontWeight: font.weight.medium },
  hint: { fontSize: font.size.sm, color: color.textMuted },
});
