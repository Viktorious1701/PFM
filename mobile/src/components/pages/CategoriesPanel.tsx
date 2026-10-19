/**
 * Categories, opened from the Activity tab: every income and expense
 * category, with rename (CM-US-04) and archive (CM-US-05). Archiving takes
 * a category out of the pickers; transactions already in it keep it.
 * New categories are still created inline while adding a transaction.
 */
import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { archiveCategory, renameCategory } from '../../api/categories';
import { errorMessage } from '../../api/errors';
import type { CategoryRead } from '../../api/types';
import { font, moon } from '../../theme/moonlit';
import { Button, Confirm, ErrorText, Field, Muted, Panel, ui } from '../ui/moon';

function CategoryRow({ c, onChanged }: { c: CategoryRead; onChanged: () => Promise<void> }) {
  const [mode, setMode] = useState<'view' | 'menu' | 'rename' | 'archive'>('view');
  const [name, setName] = useState(c.name);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await fn();
      await onChanged();
      setMode('view');
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={styles.rowWrap} testID={`category-row-${c.name}`}>
      <Pressable accessibilityRole="button" onPress={() => setMode(mode === 'view' ? 'menu' : 'view')} style={styles.row}>
        <Text style={styles.name} numberOfLines={1}>
          {c.name}
        </Text>
        <Text style={styles.chev}>{mode === 'view' ? '›' : '‹'}</Text>
      </Pressable>
      {mode === 'menu' ? (
        <View style={ui.row}>
          <Button small kind="ghost" label="Rename" onPress={() => setMode('rename')} testID="category-rename" />
          <Button small kind="danger" label="Archive" onPress={() => setMode('archive')} testID="category-archive" />
        </View>
      ) : mode === 'rename' ? (
        <View style={styles.form}>
          <Field label="Category name" value={name} onChangeText={setName} testID="category-rename-field" autoFocus />
          <View style={ui.row}>
            <Button
              small
              label="Save"
              busy={busy}
              testID="category-rename-save"
              onPress={() => (name.trim() ? void run(() => renameCategory(c.id, name.trim())) : setError('A category needs a name.'))}
            />
            <Button small kind="ghost" label="Cancel" onPress={() => setMode('view')} />
          </View>
        </View>
      ) : mode === 'archive' ? (
        <Confirm
          question={`Archive “${c.name}”? It won't be offered for new transactions; past ones keep it.`}
          confirmLabel="Archive"
          busy={busy}
          testID="category-archive-confirm"
          onConfirm={() => void run(() => archiveCategory(c.id))}
          onCancel={() => setMode('view')}
        />
      ) : null}
      {error ? <ErrorText>{error}</ErrorText> : null}
    </View>
  );
}

export function CategoriesPanel({ categories, onChanged, onClose }: { categories: CategoryRead[]; onChanged: () => Promise<void>; onClose: () => void }) {
  const groups = [
    { title: 'Income', items: categories.filter((c) => c.type === 'INCOME') },
    { title: 'Expense', items: categories.filter((c) => c.type === 'EXPENSE') },
  ];
  return (
    <Panel style={styles.panel} testID="categories-panel">
      <View style={styles.head}>
        <Text style={styles.title}>Categories</Text>
        <Button small kind="ghost" label="Done" onPress={onClose} testID="categories-done" />
      </View>
      {groups.map((g) => (
        <View key={g.title} style={styles.group}>
          <Text style={styles.groupTitle}>{g.title}</Text>
          {g.items.length === 0 ? (
            <Muted>None yet — add one while recording a transaction.</Muted>
          ) : (
            g.items.map((c, i) => (
              <View key={c.id}>
                {i > 0 ? <View style={styles.divider} /> : null}
                <CategoryRow c={c} onChanged={onChanged} />
              </View>
            ))
          )}
        </View>
      ))}
    </Panel>
  );
}

const styles = StyleSheet.create({
  panel: { gap: 18 },
  head: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  title: { fontFamily: font.semibold, fontSize: 18, color: moon.ink },
  group: { gap: 4 },
  groupTitle: { fontFamily: font.semibold, fontSize: 11, letterSpacing: 2.5, textTransform: 'uppercase', color: moon.muted, marginBottom: 4 },
  divider: { height: 1, backgroundColor: moon.hairline },
  rowWrap: { paddingVertical: 8, gap: 10 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12, cursor: 'pointer' },
  name: { flex: 1, fontFamily: font.semibold, fontSize: 16, color: moon.inkSoft },
  chev: { fontFamily: font.medium, fontSize: 18, color: moon.muted },
  form: { gap: 10 },
});
