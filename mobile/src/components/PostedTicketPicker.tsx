/**
 * Inline "posted ticket" picker — replaces `PickerSheet` at the two required
 * fields on the Add-Transaction form (Wallet, Category).
 *
 * **Why this exists**: a live ergonomics complaint against the sheet-based
 * picker there — opening it takes a tap, then a wait for the slide-up
 * animation, before any option is even visible, which is tiring to reach
 * for repeatedly on a form used every time a transaction is logged. This
 * renders every option inline, in the form's own flow, the instant the
 * screen opens — nothing to open, nothing to wait for.
 *
 * Visual language, approved via an HTML concept comparison (three options,
 * "Posted Up" chosen): each option is a small torn-top ticket "pinned" to
 * the page at a resting tilt, like notices tacked to a corkboard. Selecting
 * one fires a nail up through its corner — the nail is the persistent
 * selected-state marker, replacing a plain checkmark, with a brief punch/
 * impact flourish (trail, ink ring, corkboard splinters) the moment it
 * lands. Unselected tickets stay at their tilt; the selected one flattens
 * to true horizontal, matching a real pinned note.
 *
 * `PickerSheet` (bottom-sheet-in-a-modal) is intentionally left as-is for
 * the Transactions list's *filter* chips — those are optional, secondary
 * controls opened occasionally, not a required field reached for on every
 * single use, so the ergonomics complaint doesn't apply there.
 */
import type { ReactNode } from 'react';
import { useEffect, useRef } from 'react';
import { Animated, Easing, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { color, font, radius, space } from '../theme/tokens';
import { TornEdge } from './icons/TornEdge';

export type PostedTicketOption<T extends string> = {
  value: T;
  label: string;
  sublabel?: string;
};

type PostedTicketPickerProps<T extends string> = {
  options: PostedTicketOption<T>[];
  selected: T | null;
  onSelect: (value: T) => void;
  emptyLabel?: string;
  disabled?: boolean;
  error?: string;
  /** Rendered directly below the ticket row — e.g. the category picker's
   * inline "+ New category" mini-form. This component only owns the slot. */
  footer?: ReactNode;
  testID?: string;
  errorTestID?: string;
  ticketTestID?: (value: T) => string;
};

/** Resting tilt per ticket, cycling for any number of options — matches the
 * approved concept's "posted at odd angles" look, never perfectly level. */
const REST_TILT_DEG = [-3, 2, -1.5, 2.5, -2.5, 1.5, -3.5, 2.2];

const FIRE_DURATION_MS = 550;

export function PostedTicketPicker<T extends string>({
  options,
  selected,
  onSelect,
  emptyLabel = 'Nothing to pick yet',
  disabled,
  error,
  footer,
  testID,
  errorTestID,
  ticketTestID,
}: PostedTicketPickerProps<T>) {
  return (
    <View testID={testID}>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.row}
        keyboardShouldPersistTaps="handled"
      >
        {options.length === 0 ? (
          <Text style={styles.emptyLabel}>{emptyLabel}</Text>
        ) : (
          options.map((option, index) => (
            <Ticket
              key={option.value}
              option={option}
              restTiltDeg={REST_TILT_DEG[index % REST_TILT_DEG.length]}
              isSelected={selected === option.value}
              disabled={disabled}
              onPress={() => onSelect(option.value)}
              testID={ticketTestID?.(option.value)}
            />
          ))
        )}
      </ScrollView>
      {error ? (
        <Text testID={errorTestID} style={styles.errorText}>
          {error}
        </Text>
      ) : null}
      {footer}
    </View>
  );
}

function Ticket<T extends string>({
  option,
  restTiltDeg,
  isSelected,
  disabled,
  onPress,
  testID,
}: {
  option: PostedTicketOption<T>;
  restTiltDeg: number;
  isSelected: boolean;
  disabled?: boolean;
  onPress: () => void;
  testID?: string;
}) {
  const progress = useRef(new Animated.Value(0)).current;
  const wasSelected = useRef(false);

  useEffect(() => {
    if (isSelected && !wasSelected.current) {
      progress.setValue(0);
      Animated.timing(progress, {
        toValue: 1,
        duration: FIRE_DURATION_MS,
        easing: Easing.out(Easing.exp),
        useNativeDriver: true,
      }).start();
    } else if (!isSelected && wasSelected.current) {
      Animated.timing(progress, {
        toValue: 0,
        duration: 150,
        easing: Easing.inOut(Easing.ease),
        useNativeDriver: true,
      }).start();
    }
    wasSelected.current = isSelected;
  }, [isSelected, progress]);

  // Ticket body: tilted at rest, flattens and takes a small downward hit as
  // the nail lands, settles just below its original resting line.
  const ticketRotate = progress.interpolate({
    inputRange: [0, 0.58, 0.7, 1],
    outputRange: [`${restTiltDeg}deg`, `${restTiltDeg * 0.25}deg`, '0deg', '0deg'],
  });
  const ticketTranslateY = progress.interpolate({
    inputRange: [0, 0.7, 1],
    outputRange: [0, 3, 2],
  });

  // The nail: fired up from below, overshoots past its resting spot, settles.
  const nailTranslateY = progress.interpolate({
    inputRange: [0, 0.6, 0.78, 1],
    outputRange: [48, -6, 2, 0],
  });
  const nailRotate = progress.interpolate({
    inputRange: [0, 0.6, 0.78, 1],
    outputRange: ['-40deg', '-3deg', '-14deg', '-10deg'],
  });
  const nailScale = progress.interpolate({
    inputRange: [0, 0.6, 0.78, 1],
    outputRange: [0.35, 1.3, 0.92, 1],
    extrapolate: 'clamp',
  });
  const nailOpacity = progress.interpolate({
    inputRange: [0, 0.3, 1],
    outputRange: [0, 1, 1],
    extrapolate: 'clamp',
  });

  // Trail streak behind the nail on the way up.
  const trailScaleY = progress.interpolate({
    inputRange: [0, 0.12, 0.55, 0.72, 1],
    outputRange: [0.01, 1, 0.6, 0.01, 0.01],
    extrapolate: 'clamp',
  });
  const trailOpacity = progress.interpolate({
    inputRange: [0, 0.12, 0.55, 0.72, 1],
    outputRange: [0, 0.9, 0.45, 0, 0],
    extrapolate: 'clamp',
  });

  // Impact ring, punched outward the moment the nail lands.
  const burstScale = progress.interpolate({
    inputRange: [0.31, 0.71],
    outputRange: [0.3, 4.5],
    extrapolate: 'clamp',
  });
  const burstOpacity = progress.interpolate({
    inputRange: [0.31, 0.4, 0.71],
    outputRange: [0.9, 0.6, 0],
    extrapolate: 'clamp',
  });

  // Three corkboard splinters, kicked out on impact.
  const moteOffsets: ReadonlyArray<{ mx: number; my: number }> = [
    { mx: -11, my: -8 },
    { mx: 12, my: -5 },
    { mx: 1, my: -13 },
  ];
  const moteOpacity = progress.interpolate({
    inputRange: [0.32, 0.4, 0.72],
    outputRange: [1, 1, 0],
    extrapolate: 'clamp',
  });
  const moteScale = progress.interpolate({
    inputRange: [0.32, 0.72],
    outputRange: [1, 0.25],
    extrapolate: 'clamp',
  });

  return (
    <Pressable
      testID={testID}
      onPress={onPress}
      disabled={disabled}
      accessibilityRole="button"
      accessibilityState={{ selected: isSelected }}
      accessibilityLabel={option.sublabel ? `${option.label}, ${option.sublabel}` : option.label}
    >
      <Animated.View
        style={[
          styles.ticket,
          isSelected ? styles.ticketSelected : null,
          { transform: [{ translateY: ticketTranslateY }, { rotate: ticketRotate }] },
        ]}
      >
        <View style={styles.tornEdge}>
          <TornEdge fill={isSelected ? color.surfaceSunken : color.surface} height={8} teeth={6} />
        </View>

        <Text style={styles.label} numberOfLines={1}>
          {option.label}
        </Text>
        {option.sublabel ? (
          <Text style={styles.sublabel} numberOfLines={1}>
            {option.sublabel}
          </Text>
        ) : null}

        {isSelected ? (
          <>
            {moteOffsets.map((m, i) => (
              <Animated.View
                key={i}
                pointerEvents="none"
                style={[
                  styles.mote,
                  {
                    opacity: moteOpacity,
                    transform: [
                      {
                        translateX: progress.interpolate({
                          inputRange: [0.32, 0.72],
                          outputRange: [0, m.mx],
                          extrapolate: 'clamp',
                        }),
                      },
                      {
                        translateY: progress.interpolate({
                          inputRange: [0.32, 0.72],
                          outputRange: [0, m.my],
                          extrapolate: 'clamp',
                        }),
                      },
                      { scale: moteScale },
                    ],
                  },
                ]}
              />
            ))}
            <Animated.View
              pointerEvents="none"
              style={[styles.burst, { opacity: burstOpacity, transform: [{ scale: burstScale }] }]}
            />
            <Animated.View
              pointerEvents="none"
              style={[styles.trail, { opacity: trailOpacity, transform: [{ scaleY: trailScaleY }] }]}
            />
            <Animated.View
              pointerEvents="none"
              style={[
                styles.nail,
                {
                  opacity: nailOpacity,
                  transform: [{ translateY: nailTranslateY }, { rotate: nailRotate }, { scale: nailScale }],
                },
              ]}
            />
          </>
        ) : null}
      </Animated.View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: { gap: space.md, paddingTop: space.md, paddingBottom: space.xs, paddingHorizontal: space.xs },
  emptyLabel: { fontFamily: font.family.body, fontSize: font.size.sm, color: color.textMuted },

  ticket: {
    position: 'relative',
    minWidth: 108,
    backgroundColor: color.surface,
    borderWidth: 1,
    borderColor: color.border,
    borderRadius: radius.sm,
    paddingTop: space.md,
    paddingHorizontal: space.sm,
    paddingBottom: space.sm,
  },
  ticketSelected: {
    backgroundColor: color.surfaceSunken,
    borderColor: color.borderInteractive,
  },
  tornEdge: { position: 'absolute', top: -6, left: 0, right: 0, height: 8 },

  label: { fontFamily: font.family.heading, fontSize: font.size.sm, color: color.text },
  sublabel: { fontFamily: font.family.body, fontSize: font.size.xs, color: color.textMuted, marginTop: space.xs / 2 },

  nail: {
    position: 'absolute',
    top: -9,
    left: 10,
    width: 15,
    height: 15,
    borderRadius: 8,
    backgroundColor: color.brassSoft,
    borderWidth: 1,
    borderColor: color.brassDeep,
  },
  trail: {
    position: 'absolute',
    top: -2,
    left: 16,
    width: 3,
    height: 42,
    borderRadius: 2,
    backgroundColor: color.brassSoft,
  },
  burst: {
    position: 'absolute',
    top: -2,
    left: 15,
    width: 4,
    height: 4,
    marginLeft: -2,
    marginTop: -2,
    borderRadius: 2,
    borderWidth: 1.5,
    borderColor: color.expense,
  },
  mote: {
    position: 'absolute',
    top: -2,
    left: 15,
    width: 2.5,
    height: 2.5,
    marginLeft: -1.25,
    marginTop: -1.25,
    borderRadius: 1,
    backgroundColor: color.brassDeep,
  },

  errorText: {
    fontSize: font.size.sm,
    color: color.error.fg,
    fontFamily: font.family.bodyMedium,
    marginTop: space.xs,
  },
});
