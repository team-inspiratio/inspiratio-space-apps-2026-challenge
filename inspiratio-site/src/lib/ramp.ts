import { interpolateRgbBasis } from 'd3'

// Sequential ramps for a light background, "more" is always darker.
export const PALETTES = {
  fire: ['#fbe7b1', '#f7c56f', '#f19a45', '#e2662d', '#c0392b', '#8a1f2d', '#4f1325'],
  // cividis, reversed so that more detections read darker; designed for colour-vision deficiency.
  cividis: ['#f2e15a', '#cbba69', '#9c9474', '#757373', '#4f566e', '#2c3c67', '#00204d'],
}
export type PaletteName = keyof typeof PALETTES

export let STOPS = PALETTES.fire
export let LUT: string[] = []
export let GRADIENT = ''
export function setPalette(p: PaletteName) {
  STOPS = PALETTES[p]
  const interp = interpolateRgbBasis(STOPS)
  LUT = Array.from({ length: 256 }, (_, i) => interp(i / 255))
  GRADIENT = `linear-gradient(90deg, ${STOPS.join(', ')})`
}
setPalette('fire')

/** 0..1 → css colour. */
export const ramp = (t: number) => LUT[Math.max(0, Math.min(255, Math.round(t * 255)))]
export const logT = (v: number, vmax: number) => (v <= 0 ? 0 : Math.min(1, Math.log1p(v) / Math.log1p(vmax)))
export const ZERO = '#ece9e2'

/** Log scale between a low and a high value (for totals that never get close to zero). */
export const logRange = (v: number, lo: number, hi: number) =>
  v <= 0 ? 0 : Math.max(0, Math.min(1, (Math.log(v) - Math.log(lo)) / (Math.log(hi) - Math.log(lo))))

// Diverging ramp for the anomaly layer: below normal is blue, above is fire.
const DIV = interpolateRgbBasis(['#2f6ea6', '#8fb8d8', '#e6e2d8', '#f2a35a', '#c0392b', '#5e1426'])
export const DIV_LUT = Array.from({ length: 256 }, (_, i) => DIV(i / 255))
/** ratio → css colour, log2 scale clamped at ¼× … 8×. */
export const anomalyColor = (ratio: number) => {
  const l = Math.log2(Math.max(1e-3, ratio))
  const t = l < 0 ? 0.5 + 0.5 * Math.max(-1, l / 2) : 0.5 + 0.5 * Math.min(1, l / 3)
  return DIV_LUT[Math.round(t * 255)]
}
export const DIV_GRADIENT = `linear-gradient(90deg, #2f6ea6, #8fb8d8, #e6e2d8, #f2a35a, #c0392b, #5e1426)`
