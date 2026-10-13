/**
 * Tab shell.
 *
 * `Tabs` is imported from 'expo-router/js-tabs', NOT from 'expo-router'.
 * In expo-router 57 the root re-export is a deprecated getter that resolves to
 * `undefined` at runtime, crashing this layout with "Element type is invalid".
 * See node_modules/expo-router/build/exports.js:111. docs.expo.dev still shows
 * the old root import — the package source is authoritative. (ADR-0009)
 *
 * Chrome is now Nullscapes, matching the validated zoom-traversal mockups
 * exactly ("Glitch-only theme, no Cash & Carry chrome"):
 * - `headerShown: false` everywhere — the installed react-navigation
 *   version's `headerTransparent` leaves content needing `useHeaderHeight()`
 *   to avoid sliding under the floating header, and that hook isn't
 *   re-exported from the public `expo-router` entrypoint in this version
 *   (confirmed against the bundled `react-navigation/elements` build). Each
 *   screen renders its own `NullscapesHeader` instead (via `Screen`), which
 *   reserves its own real layout space and needs no such workaround.
 * - `tabBarStyle` is `position:'absolute'` + `backgroundColor:'transparent'`,
 *   with a `tabBarBackground` render prop painting the mockups' own
 *   `rgba(11,14,19,0.9)` tint behind the bar — `BottomTabBar` auto-clears its
 *   own background to transparent once `tabBarBackground` is supplied.
 * - Tab icons dropped `PostmarkIcon`'s dashed-ring/solid-stamp-fill
 *   treatment (that "stamped badge" metaphor is being retired app-wide) in
 *   favor of a plain glyph + mint underline on the active tab, exactly as
 *   the mockups show — no ring, no badge.
 */
import { Tabs } from 'expo-router/js-tabs';
import type { ColorValue } from 'react-native';
import { StyleSheet, Text, View } from 'react-native';
import Svg from 'react-native-svg';

import {
  BudgetsGlyph,
  DashboardGlyph,
  FamilyGlyph,
  TransactionsGlyph,
  WalletsGlyph,
} from '../../src/components/icons/Glyphs';
import { NullscapesScene } from '../../src/components/icons/NullscapesScene';
import { TabCameraSync, tabNearScale } from '../../src/lib/tabCameraScale';
import { ns, nsFont } from '../../src/theme/nullscapes';

const TAB_ICON_SIZE = 22;

function TabGlyphIcon({ focused, glyph }: { focused: boolean; glyph: (color: string) => React.ReactNode }) {
  const tint = focused ? ns.mint : ns.tabInactive;
  return (
    <Svg width={TAB_ICON_SIZE} height={TAB_ICON_SIZE} viewBox="0 0 24 24">
      {glyph(tint)}
    </Svg>
  );
}

function TabBarLabel({
  focused,
  color: tint,
  children,
}: {
  focused: boolean;
  color: ColorValue;
  children: string;
}) {
  return (
    <View style={[styles.labelWrap, focused ? styles.labelWrapActive : null]}>
      <Text
        style={{
          fontFamily: focused ? nsFont.semibold : nsFont.regular,
          fontSize: 11,
          color: tint,
        }}
      >
        {children}
      </Text>
    </View>
  );
}

export default function TabsLayout() {
  return (
    <View style={styles.root}>
      {/* Mounted ONCE here, as a sibling of `<Tabs>` — never inside a
          `Tabs.Screen` — so it persists across every tab switch instead of
          living/dying with whichever screen last mounted it. `tabNearScale`
          (`src/lib/tabCameraScale.ts`) drives the cross-tab "camera zoom";
          `TabCameraSync` is the only thing that writes to it, kept separate
          so this component's own props never change identity. */}
      <NullscapesScene style={styles.background} tabScale={tabNearScale} />
      <TabCameraSync />
      <Tabs
        screenOptions={{
          headerShown: false,
          tabBarActiveTintColor: ns.mint,
          tabBarInactiveTintColor: ns.tabInactive,
          tabBarStyle: {
            position: 'absolute',
            backgroundColor: 'transparent',
            borderTopColor: ns.chromeBorder,
            borderTopWidth: 1,
          },
          tabBarBackground: () => (
            <View style={[StyleSheet.absoluteFill, { backgroundColor: ns.chromeBg }]} />
          ),
          tabBarLabel: (props) => <TabBarLabel {...props} />,
        }}
      >
        <Tabs.Screen
          name="index"
          options={{
            title: 'Dashboard',
            tabBarIcon: ({ focused }) => (
              <TabGlyphIcon focused={focused} glyph={(c) => <DashboardGlyph color={c} />} />
            ),
          }}
        />
        <Tabs.Screen
          name="transactions/index"
          options={{
            title: 'Transactions',
            tabBarIcon: ({ focused }) => (
              <TabGlyphIcon focused={focused} glyph={(c) => <TransactionsGlyph color={c} />} />
            ),
          }}
        />
        <Tabs.Screen
          name="wallets/index"
          options={{
            title: 'Wallets',
            tabBarIcon: ({ focused }) => (
              <TabGlyphIcon focused={focused} glyph={(c) => <WalletsGlyph color={c} />} />
            ),
          }}
        />
        <Tabs.Screen
          name="budgets/index"
          options={{
            title: 'Budgets',
            tabBarIcon: ({ focused }) => (
              <TabGlyphIcon focused={focused} glyph={(c) => <BudgetsGlyph color={c} />} />
            ),
          }}
        />
        <Tabs.Screen
          name="users/index"
          options={{
            title: 'Family',
            tabBarIcon: ({ focused }) => (
              <TabGlyphIcon focused={focused} glyph={(c) => <FamilyGlyph color={c} />} />
            ),
          }}
        />
        {/* Hide sub-routes from tab bar */}
        <Tabs.Screen name="transactions/create" options={{ href: null, title: 'Log Expense' }} />
        <Tabs.Screen name="wallets/create" options={{ href: null, title: 'Add Wallet' }} />
        <Tabs.Screen name="budgets/create" options={{ href: null, title: 'Set Budget' }} />
        <Tabs.Screen name="users/invite" options={{ href: null, title: 'Invite Member' }} />
        <Tabs.Screen name="reports/index" options={{ href: null, title: 'Financial Reports' }} />
      </Tabs>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  // A plain literal, same as the Dashboard's own pre-existing full-bleed
  // style — NOT `StyleSheet.absoluteFill`. That library-provided constant is
  // itself built via `StyleSheet.create` at react-native-web's module-load
  // time; something about that path (vs. a style declared and flattened
  // within the same `StyleSheet.create` call that owns it) stops
  // `NullscapesSceneRich`/`Lite`'s own `StyleSheet.flatten(style)?.position
  // === 'absolute'` full-bleed detection from resolving back to the literal
  // string `'absolute'`, silently collapsing the background to its small
  // boxed-aspect-ratio size instead of the full screen.
  background: { position: 'absolute', top: 0, left: 0, right: 0, bottom: 0 },
  labelWrap: { paddingBottom: 4, borderBottomWidth: 2, borderBottomColor: 'transparent' },
  labelWrapActive: { borderBottomColor: ns.mint },
});
