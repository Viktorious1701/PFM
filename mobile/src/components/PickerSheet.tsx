/**
 * Generic "pick one from a list in a bottom sheet" — a deliberate, justified
 * exception to this codebase's bespoke-per-screen component convention: a
 * picker sheet has no screen-specific visual identity, and it is needed at
 * four call sites (wallet/category filter chips on the Transactions list,
 * wallet/category pickers on the Add-Transaction form).
 *
 * RN `Modal` (`transparent`, `animationType="slide"`), a backdrop `Pressable`
 * that closes on tap-outside, and a `surface`-coloured sheet sliding up from
 * the bottom with `radius.lg` top corners. This design system has a flat-
 * depth rule (DESIGN.md "Elevation & Depth" — no drop-shadow on anything
 * resting on the page), so the sheet is separated from the backdrop with a
 * hairline border only, never a shadow.
 *
 * **Real bug found and fixed**: the sheet used to be nested *inside* the
 * backdrop `Pressable` (with a `stopPropagation()` no-op `onPress` to stop a
 * tap on the sheet from also closing it) — a live verification pass found
 * this renders as a `<button>` nested inside a `<button>` on the web target
 * (confirmed via a real React DOM console error naming this file), which is
 * invalid HTML and produces exactly the kind of unpredictable click-routing
 * this codebase fought all session (e.g. selecting one option, then having
 * the *next* tap land on stale sheet content). The backdrop and the sheet
 * are now **siblings**, not parent/child — the sheet is a plain `View`
 * positioned on top of a full-screen backdrop `Pressable`, so a tap on the
 * sheet or its rows never reaches the backdrop's own handler in the first
 * place, and no `stopPropagation()` workaround is needed at all.
 */
import type { JSX, ReactNode } from 'react';
import { Modal, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { color, font, radius, space, textStyle } from '../theme/tokens';

export type PickerOption<T extends string> = { value: T; label: string };

type PickerSheetProps<T extends string> = {
  visible: boolean;
  title: string;
  options: PickerOption<T>[];
  selected: T | null;
  onSelect: (value: T | null) => void;
  onClose: () => void;
  /** Shows a leading "All"/`clearLabel` row above the option list that selects `null`. */
  allowClear?: boolean;
  clearLabel?: string;
  /**
   * Rendered below the option list — e.g. the category picker's inline
   * "+ New category" mini-form. This component only owns the slot, not its
   * content.
   */
  footer?: ReactNode;
};

export function PickerSheet<T extends string>({
  visible,
  title,
  options,
  selected,
  onSelect,
  onClose,
  allowClear = false,
  clearLabel = 'All',
  footer,
}: PickerSheetProps<T>): JSX.Element {
  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <View style={styles.overlay}>
        <Pressable
          style={[StyleSheet.absoluteFill, styles.backdrop]}
          onPress={onClose}
          accessibilityRole="button"
          accessibilityLabel="Close"
        />

        <View style={styles.sheet}>
          <Text style={styles.title}>{title}</Text>

          <ScrollView style={styles.optionList} keyboardShouldPersistTaps="handled">
            {allowClear ? (
              <PickerRow label={clearLabel} selected={selected === null} onPress={() => onSelect(null)} />
            ) : null}
            {options.map((option) => (
              <PickerRow
                key={option.value}
                label={option.label}
                selected={selected === option.value}
                onPress={() => onSelect(option.value)}
              />
            ))}
          </ScrollView>

          {footer ? <View style={styles.footer}>{footer}</View> : null}
        </View>
      </View>
    </Modal>
  );
}

function PickerRow({
  label,
  selected,
  onPress,
}: {
  label: string;
  selected: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      style={styles.row}
      onPress={onPress}
      accessibilityRole="button"
      accessibilityState={{ selected }}
    >
      <Text style={[styles.rowLabel, selected ? styles.rowLabelSelected : null]}>{label}</Text>
      {selected ? <Text style={styles.rowCheck}>✓</Text> : null}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  // Positions the sheet at the bottom of the screen. No background color of
  // its own — the backdrop `Pressable` (a sibling, absolutely filled behind
  // the sheet) supplies the dim color, so the two can be separate elements
  // instead of one nesting inside the other.
  overlay: { flex: 1, justifyContent: 'flex-end' },
  backdrop: { backgroundColor: 'rgba(43,36,32,0.35)' },
  sheet: {
    backgroundColor: color.surface,
    borderTopLeftRadius: radius.lg,
    borderTopRightRadius: radius.lg,
    borderTopWidth: 1,
    borderLeftWidth: 1,
    borderRightWidth: 1,
    borderColor: color.border,
    maxHeight: '70%',
    paddingTop: space.lg,
    paddingBottom: space.xl,
  },
  title: {
    fontFamily: font.family.heading,
    fontSize: font.size.lg,
    color: color.text,
    paddingHorizontal: space.xl,
    marginBottom: space.sm,
  },
  optionList: { flexGrow: 0 },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: space.md,
    paddingHorizontal: space.xl,
    borderTopWidth: 1,
    borderTopColor: color.border,
  },
  rowLabel: { ...textStyle.body },
  rowLabelSelected: { fontFamily: font.family.bodyMedium },
  rowCheck: { fontFamily: font.family.bodyMedium, fontSize: font.size.body, color: color.text },
  footer: {
    paddingHorizontal: space.xl,
    paddingTop: space.md,
    borderTopWidth: 1,
    borderTopColor: color.border,
  },
});
