/**
 * Labelled text input with inline error text.
 *
 * The error slot matters for spec AC-03: the validation message has to identify
 * the offending field, not just appear somewhere on the screen.
 */
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

export function TextField({ label, error, errorTestID, hint, style, ...inputProps }: Props) {
  return (
    <View style={styles.container}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        style={[styles.input, error ? styles.inputError : null, style]}
        placeholderTextColor={color.textMuted}
        accessibilityLabel={label}
        {...inputProps}
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
  label: { fontSize: font.size.sm, fontWeight: font.weight.semibold, color: color.textMuted },
  input: {
    borderWidth: 1,
    borderColor: color.border,
    backgroundColor: color.surface,
    padding: space.md,
    borderRadius: radius.md,
    fontSize: font.size.lg,
    color: color.text,
  },
  inputError: { borderColor: color.error.accent },
  error: { fontSize: font.size.sm, color: color.error.fg, fontWeight: font.weight.medium },
  hint: { fontSize: font.size.sm, color: color.textMuted },
});
