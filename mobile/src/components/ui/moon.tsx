/**
 * Building blocks for the pages over the moonlit scene — one look for every
 * tab: translucent night-blue panels, Rajdhani type, pill controls.
 */
import { useState, type ReactNode } from 'react';
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
  type KeyboardTypeOptions,
  type StyleProp,
  type ViewStyle,
} from 'react-native';

import { font, moon } from '../../theme/moonlit';

export function Panel({ children, style, testID }: { children: ReactNode; style?: StyleProp<ViewStyle>; testID?: string }) {
  return (
    <View style={[s.panel, style]} testID={testID}>
      {children}
    </View>
  );
}

/** Small uppercase heading above a group, with an optional value or
 * action on the right. */
export function SectionHead({ title, right }: { title: string; right?: ReactNode }) {
  return (
    <View style={s.sectionHead}>
      <Text style={s.label}>{title}</Text>
      {typeof right === 'string' ? <Text style={[s.label, { color: moon.inkSoft }]}>{right}</Text> : right}
    </View>
  );
}

export function Label({ children }: { children: ReactNode }) {
  return <Text style={s.fieldLabel}>{children}</Text>;
}

export function Field({
  label,
  value,
  onChangeText,
  placeholder,
  keyboardType,
  testID,
  autoFocus,
  onSubmitEditing,
  secure,
}: {
  label: string;
  value: string;
  onChangeText: (v: string) => void;
  placeholder?: string;
  keyboardType?: KeyboardTypeOptions;
  testID?: string;
  autoFocus?: boolean;
  onSubmitEditing?: () => void;
  /** Password entry. */
  secure?: boolean;
}) {
  const [focused, setFocused] = useState(false);
  return (
    <View style={s.fieldGroup}>
      <Label>{label}</Label>
      <TextInput
        testID={testID}
        accessibilityLabel={label}
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={moon.muted}
        keyboardType={keyboardType}
        autoFocus={autoFocus}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        onSubmitEditing={onSubmitEditing}
        secureTextEntry={secure}
        autoCapitalize={secure ? 'none' : undefined}
        style={[s.input, focused && s.inputFocused]}
      />
    </View>
  );
}

/** A single-choice row of pills. */
export function Chips<T extends string>({
  label,
  options,
  value,
  onChange,
  testID,
}: {
  label?: string;
  options: readonly { value: T; label: string }[];
  value: T | null;
  onChange: (v: T) => void;
  testID?: string;
}) {
  return (
    <View style={s.fieldGroup}>
      {label ? <Label>{label}</Label> : null}
      <View style={s.chips} testID={testID}>
        {options.map((o) => {
          const on = o.value === value;
          return (
            <Pressable
              key={o.value}
              testID={testID ? `${testID}-${o.label}` : undefined}
              role="radio"
              aria-checked={on}
              onPress={() => onChange(o.value)}
              style={({ pressed }) => [s.chip, on && s.chipOn, pressed && s.pressed]}
            >
              <Text style={[s.chipText, on && s.chipTextOn]} numberOfLines={1}>
                {o.label}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

export function Button({
  label,
  onPress,
  kind = 'primary',
  busy,
  disabled,
  testID,
  small,
}: {
  label: string;
  onPress: () => void;
  kind?: 'primary' | 'ghost' | 'danger';
  busy?: boolean;
  disabled?: boolean;
  testID?: string;
  small?: boolean;
}) {
  const off = busy || disabled;
  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityState={{ disabled: !!off, busy: !!busy }}
      onPress={off ? undefined : onPress}
      style={({ pressed }) => [
        s.button,
        small && s.buttonSmall,
        kind === 'primary' ? s.primary : kind === 'danger' ? s.danger : s.ghost,
        (pressed || off) && s.pressed,
      ]}
    >
      {busy ? (
        <ActivityIndicator color={kind === 'primary' ? '#0c1727' : moon.ink} />
      ) : (
        <Text style={[s.buttonText, kind === 'primary' ? s.primaryText : kind === 'danger' ? s.dangerText : null]}>
          {label}
        </Text>
      )}
    </Pressable>
  );
}

export function ErrorText({ children }: { children: ReactNode }) {
  return (
    <Text style={s.error} accessibilityRole="alert">
      {children}
    </Text>
  );
}

export function Muted({ children }: { children: ReactNode }) {
  return <Text style={s.muted}>{children}</Text>;
}

export function Loading({ label }: { label: string }) {
  return (
    <View style={s.loading}>
      <ActivityIndicator color={moon.ink} accessibilityLabel={label} />
    </View>
  );
}

/** Load failure with a retry. */
export function LoadError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <Panel style={s.center}>
      <Text style={s.body}>{message}</Text>
      <Button kind="ghost" small label="Try again" onPress={onRetry} />
    </Panel>
  );
}

/** Inline "are you sure" — two buttons in place of the one that asked. */
export function Confirm({
  question,
  confirmLabel,
  onConfirm,
  onCancel,
  busy,
  testID,
}: {
  question: string;
  confirmLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
  busy?: boolean;
  testID?: string;
}) {
  return (
    <View style={s.confirm}>
      <Text style={s.body}>{question}</Text>
      <View style={s.row}>
        <Button small kind="ghost" label="Cancel" onPress={onCancel} />
        <Button small kind="danger" label={confirmLabel} onPress={onConfirm} busy={busy} testID={testID} />
      </View>
    </View>
  );
}

export const ui = StyleSheet.create({
  /** The page's centered reading column. */
  column: { width: '100%', maxWidth: 720, alignSelf: 'center', paddingHorizontal: 16, gap: 22 },
  section: { gap: 12 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 8, flexWrap: 'wrap' },
  num: { fontVariant: ['tabular-nums'] },
});

const label = {
  fontFamily: font.semibold,
  fontSize: 12,
  letterSpacing: 3,
  textTransform: 'uppercase' as const,
  color: moon.muted,
};

const s = StyleSheet.create({
  panel: {
    padding: 20,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: moon.panelBorder,
    backgroundColor: moon.panel,
  },
  sectionHead: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 4, minHeight: 24 },
  label,
  fieldGroup: { gap: 6 },
  fieldLabel: { ...label, fontSize: 11, letterSpacing: 2, color: moon.inkSoft },
  input: {
    fontFamily: font.medium,
    fontSize: 17,
    color: moon.ink,
    paddingVertical: 9,
    paddingHorizontal: 12,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: moon.fieldBorder,
    backgroundColor: moon.field,
  },
  inputFocused: { borderColor: moon.focus },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  chip: {
    height: 32,
    justifyContent: 'center',
    paddingHorizontal: 13,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: moon.fieldBorder,
    backgroundColor: moon.field,
    maxWidth: 220,
  },
  chipOn: { borderColor: moon.focus, backgroundColor: 'rgba(169,200,255,0.16)' },
  chipText: { fontFamily: font.semibold, fontSize: 14, color: moon.inkSoft, letterSpacing: 0.3 },
  chipTextOn: { color: moon.ink },
  button: { height: 42, paddingHorizontal: 20, borderRadius: 999, alignItems: 'center', justifyContent: 'center' },
  buttonSmall: { height: 34, paddingHorizontal: 14 },
  primary: { backgroundColor: 'rgba(223,232,251,0.9)' },
  ghost: { borderWidth: 1, borderColor: moon.panelBorder, backgroundColor: 'rgba(10,18,32,0.55)' },
  danger: { borderWidth: 1, borderColor: 'rgba(255,155,155,0.5)', backgroundColor: 'rgba(255,155,155,0.12)' },
  buttonText: { fontFamily: font.bold, fontSize: 12, letterSpacing: 2.5, textTransform: 'uppercase', color: moon.ink },
  primaryText: { color: '#0c1727' },
  dangerText: { color: moon.danger },
  pressed: { opacity: 0.65 },
  error: { fontFamily: font.medium, fontSize: 15, color: moon.danger },
  muted: { fontFamily: font.medium, fontSize: 15, color: moon.muted },
  body: { fontFamily: font.medium, fontSize: 16, color: moon.inkSoft },
  loading: { paddingVertical: 40, alignItems: 'center' },
  center: { alignItems: 'center', gap: 14 },
  confirm: { gap: 10 },
  row: { flexDirection: 'row', gap: 8, flexWrap: 'wrap' },
});
