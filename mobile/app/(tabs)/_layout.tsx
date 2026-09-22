/**
 * Tab shell.
 *
 * `Tabs` is imported from 'expo-router/js-tabs', NOT from 'expo-router'.
 * In expo-router 57 the root re-export is a deprecated getter that resolves to
 * `undefined` at runtime, crashing this layout with "Element type is invalid".
 * See node_modules/expo-router/build/exports.js:111. docs.expo.dev still shows
 * the old root import — the package source is authoritative. (ADR-0009)
 *
 * Chrome per DESIGN.md "screen chrome": `surface` bar with a `border` top
 * hairline (never a shadow, per the flat depth rule), ink active tint /
 * Faded Ink inactive, Courier Prime header titles.
 *
 * Tab icons are the same `PostmarkIcon` + glyph system as the Dashboard's
 * category row (DESIGN.md "postmark category glyph"), replacing the earlier
 * raw-emoji `tabBarIcon`s. `focused` drives `active` on the icon and the
 * glyph's own `color`, so the active tab renders as a solid stamped badge —
 * see PostmarkIcon's own doc comment for why inactive defaults to `color.text`
 * but this screen passes `color.textMuted` explicitly.
 *
 * The label weight also needs to switch with focus (Bold cut when active,
 * Regular when not), which a static `tabBarLabelStyle` object cannot do — it
 * is not focus-aware. `tabBarLabel` accepts a `({ focused, color, children })
 * => ReactNode` render function in this installed expo-router/react-navigation
 * version (confirmed from `node_modules/expo-router/build/react-navigation/
 * bottom-tabs/types.d.ts`), so that is used instead, defined once in
 * `screenOptions` since it already receives each screen's own title as
 * `children`.
 */
import { Tabs } from 'expo-router/js-tabs';
import type { ColorValue } from 'react-native';
import { Text } from 'react-native';

import {
  BudgetsGlyph,
  DashboardGlyph,
  FamilyGlyph,
  TransactionsGlyph,
  WalletsGlyph,
} from '../../src/components/icons/Glyphs';
import { PostmarkIcon } from '../../src/components/icons/PostmarkIcon';
import { color, font } from '../../src/theme/tokens';

/** On-screen box size for a tab-bar postmark badge — substantial, not tiny (see PostmarkIcon's `size` prop). */
const TAB_ICON_SIZE = 34;

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
    <Text
      style={{
        fontFamily: focused ? font.family.bodyMedium : font.family.body,
        fontSize: 11,
        color: tint,
      }}
    >
      {children}
    </Text>
  );
}

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: color.primary,
        tabBarInactiveTintColor: color.textMuted,
        tabBarStyle: {
          backgroundColor: color.surface,
          borderTopColor: color.border,
          borderTopWidth: 1,
        },
        tabBarLabel: (props) => <TabBarLabel {...props} />,
        headerStyle: { backgroundColor: color.surface },
        headerTintColor: color.text,
        headerTitleStyle: { fontFamily: font.family.headingSemibold, fontSize: 18 },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: 'Dashboard',
          tabBarIcon: ({ focused }) => (
            <PostmarkIcon active={focused} size={TAB_ICON_SIZE} inactiveColor={color.textMuted}>
              <DashboardGlyph color={focused ? color.surface : color.textMuted} />
            </PostmarkIcon>
          ),
        }}
      />
      <Tabs.Screen
        name="transactions/index"
        options={{
          title: 'Transactions',
          headerTitle: 'All Transactions',
          tabBarIcon: ({ focused }) => (
            <PostmarkIcon active={focused} size={TAB_ICON_SIZE} inactiveColor={color.textMuted}>
              <TransactionsGlyph color={focused ? color.surface : color.textMuted} />
            </PostmarkIcon>
          ),
        }}
      />
      <Tabs.Screen
        name="wallets/index"
        options={{
          title: 'Wallets',
          headerTitle: 'My Wallets',
          tabBarIcon: ({ focused }) => (
            <PostmarkIcon active={focused} size={TAB_ICON_SIZE} inactiveColor={color.textMuted}>
              <WalletsGlyph color={focused ? color.surface : color.textMuted} />
            </PostmarkIcon>
          ),
        }}
      />
      <Tabs.Screen
        name="budgets/index"
        options={{
          title: 'Budgets',
          headerTitle: 'Budget Status',
          tabBarIcon: ({ focused }) => (
            <PostmarkIcon active={focused} size={TAB_ICON_SIZE} inactiveColor={color.textMuted}>
              <BudgetsGlyph color={focused ? color.surface : color.textMuted} />
            </PostmarkIcon>
          ),
        }}
      />
      <Tabs.Screen
        name="users/index"
        options={{
          title: 'Family',
          headerTitle: 'Family Members',
          tabBarIcon: ({ focused }) => (
            <PostmarkIcon active={focused} size={TAB_ICON_SIZE} inactiveColor={color.textMuted}>
              <FamilyGlyph color={focused ? color.surface : color.textMuted} />
            </PostmarkIcon>
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
  );
}