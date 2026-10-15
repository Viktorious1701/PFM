import { useAudioPlayer, useAudioPlayerStatus } from 'expo-audio';
import { useEffect } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { MoonlitScene, SKY } from '../src/components/MoonlitScene';

const SONG = require('../assets/audio/nullscapes.mp3');

export default function Index() {
  const player = useAudioPlayer(SONG);
  const { playing } = useAudioPlayerStatus(player);

  useEffect(() => {
    player.loop = true;
  }, [player]);

  return (
    <View style={styles.root}>
      <MoonlitScene style={StyleSheet.absoluteFill} />
      <Pressable
        testID="play-song"
        accessibilityRole="button"
        accessibilityLabel={playing ? 'Pause Nullscapes' : 'Play Nullscapes'}
        onPress={() => (playing ? player.pause() : player.play())}
        style={({ pressed }) => [styles.button, pressed && styles.pressed]}
      >
        <Text style={styles.label}>{playing ? 'Pause' : 'Play Nullscapes'}</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: SKY },
  button: {
    position: 'absolute',
    bottom: 40,
    alignSelf: 'center',
    paddingVertical: 12,
    paddingHorizontal: 28,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: 'rgba(223,232,251,0.45)',
    backgroundColor: 'rgba(10,18,32,0.55)',
  },
  pressed: { opacity: 0.7 },
  label: {
    color: '#eaf0ff',
    fontSize: 13,
    fontWeight: '500',
    letterSpacing: 2.5,
    textTransform: 'uppercase',
  },
});
