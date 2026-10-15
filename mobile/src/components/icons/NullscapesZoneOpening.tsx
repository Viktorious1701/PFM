/**
 * "Zone 1 — Opening" — a precise redraw of the reference Nullscapes level's
 * opening section (`Nullscapes-level.gmd`, decoded and analyzed, not part
 * of this app's own code), x range roughly -2535 to 11415: the only part
 * of the level where the sky stays the header's default light blue-gray
 * (no BG Color Trigger fires again until x=11415 — see `nullscapesZones`
 * notes in the sibling Zone 2/3 components for the rest of the level).
 *
 * Every one of the 33,576 real decoration objects placed in this x range
 * is rendered here — no downsampling (unlike the earlier `NullscapesVista`
 * draft, which thinned ~15.8k points down to 381 for a lightweight
 * preview). Position, rotation, per-instance scale, color channel + HSV
 * adjustment, and Z-layer/Z-order depth sort are all real extracted
 * values from the level string; only the drawn SHAPE itself is a proxy
 * (a plain rotated rectangle) — the level's actual sprite art isn't
 * recoverable from placement data alone, only where/how big/what
 * color/how deep each piece was, which is what's reconstructed here.
 * Explicitly NOT optimized for render cost — ignore performance per this
 * recreation's own brief; correct this later if it's ever used live.
 *
 * Covers two things found in this x range: the one hand-composed "vista"
 * cluster (x -300..3500, y 4800..6800 in level space) that exists nowhere
 * else in the level, and the general corridor terrain/trim dressing for
 * the rest of the zone — both are just points in the same dataset here,
 * already combined and depth-sorted.
 *
 * Draft / not wired into any screen yet — built standalone for review.
 */
import { memo } from 'react';
import { StyleSheet, View, type ViewStyle } from 'react-native';
import Svg, { Rect } from 'react-native-svg';

import zoneData from './zoneOpeningData.json';

export const ZONE1_VIEW_W = 400;
export const ZONE1_VIEW_H = 260;

const SKY = '#E4F1F7'; // header default BG channel, rgb(228,241,247)

type ZonePoint = { x: number; y: number; rot: number; s: number; z: number; zo: number; c: string };
const POINTS = zoneData as ZonePoint[];

const BASE_SIZE = 2.6;

function NullscapesZoneOpeningImpl({ style }: { style?: ViewStyle }): React.JSX.Element {
  const fullBleed = StyleSheet.flatten(style)?.position === 'absolute';

  return (
    <View style={[fullBleed ? styles.fill : styles.wrap, style]} pointerEvents="none" importantForAccessibility="no-hide-descendants">
      <Svg width="100%" height="100%" viewBox={`0 0 ${ZONE1_VIEW_W} ${ZONE1_VIEW_H}`} preserveAspectRatio="xMidYMid slice">
        <Rect x={0} y={0} width={ZONE1_VIEW_W} height={ZONE1_VIEW_H} fill={SKY} />
        {POINTS.map((p, i) => {
          const size = BASE_SIZE * Math.max(0.15, p.s);
          return (
            <Rect
              key={i}
              x={p.x - size / 2}
              y={p.y - size / 2}
              width={size}
              height={size}
              fill={p.c}
              transform={`rotate(${p.rot} ${p.x} ${p.y})`}
            />
          );
        })}
      </Svg>
    </View>
  );
}

export const NullscapesZoneOpening = memo(NullscapesZoneOpeningImpl);

const styles = StyleSheet.create({
  wrap: { width: '100%', aspectRatio: ZONE1_VIEW_W / ZONE1_VIEW_H, borderRadius: 4, overflow: 'hidden' },
  fill: { flex: 1 },
});
