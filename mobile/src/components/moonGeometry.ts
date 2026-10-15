/** The moonlit scene's own coordinate space (the prototype's 1280x720
 * canvas) and where the moon sits in it — shared by the scene and the
 * climax burst so both draw against the same moon. */
export const W = 1280;
export const H = 720;
export const MOON_CX = W * 0.49;
export const MOON_CY = H * 0.5;
export const MOON_R = H * 0.165;

/** Screen placement of the scene for a frame of `w` x `h` px: cover-scaled
 * ("slice"), centered, edges cropped evenly. */
export function coverFit(w: number, h: number) {
  const scale = Math.max(w / W, h / H);
  return { scale, offX: (w - W * scale) / 2, offY: (h - H * scale) / 2 };
}
