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
 * hairline (never a shadow, per the flat-editorial depth rule), `sky-deep`
 * active tint / `ink-muted` inactive, Lora header titles.
 */
import { Tabs } from 'expo-router/js-tabs';
import { Text } from 'react-native';

import { color } from '../../src/theme/tokens';

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
        tabBarLabelStyle: { fontFamily: 'Inter_500Medium', fontSize: 11 },
        headerStyle: { backgroundColor: color.surface },
        headerTintColor: color.text,
        headerTitleStyle: { fontFamily: 'Lora_600SemiBold', fontSize: 18 },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: 'Dashboard',
          tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 18 }}>📊</Text>,
        }}
      />
      <Tabs.Screen
        name="transactions/index"
        options={{
          title: 'Transactions',
          headerTitle: 'All Transactions',
          tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 18 }}>💸</Text>,
        }}
      />
      <Tabs.Screen
        name="wallets/index"
        options={{
          title: 'Wallets',
          headerTitle: 'My Wallets',
          tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 18 }}>💳</Text>,
        }}
      />
      <Tabs.Screen
        name="budgets/index"
        options={{
          title: 'Budgets',
          headerTitle: 'Budget Status',
          tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 18 }}>🎯</Text>,
        }}
      />
      <Tabs.Screen
        name="users/index"
        options={{
          title: 'Family',
          headerTitle: 'Family Members',
          tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 18 }}>👥</Text>,
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