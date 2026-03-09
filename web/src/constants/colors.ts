// ── Design system color tokens ────────────────────────────────────
// Raw hex values for use with Recharts, Leaflet, and inline styles.
// Tailwind equivalents are defined in tailwind.config.ts.

export const COLORS = {
  // Background scale
  bg: {
    base:     "#05080f",
    surface:  "#080e1a",
    elevated: "#0f1623",
    border:   "#1e2a3d",
    subtle:   "#0a0e18",
  },

  // Text scale
  text: {
    primary:   "#e0e8f0",
    secondary: "#c8d8e8",
    muted:     "#7a90a8",
    faint:     "#4a6080",
  },

  // Brand green
  accent: {
    green:     "#27ae60",
    greenMid:  "#4a9060",
    greenDark: "#1a6b40",
  },

  // Forecast outcome colors
  forecast: {
    below:   "#e74c3c",   // Below Normal / drought
    near:    "#d4a017",   // Near Normal
    above:   "#27ae60",   // Above Normal
    belowBg: "rgba(231,76,60,0.12)",
    nearBg:  "rgba(212,160,23,0.12)",
    aboveBg: "rgba(39,174,96,0.12)",
  },

  // Release tier colors
  tier: {
    full:              "#27ae60",
    fullBg:            "rgba(39,174,96,0.10)",
    experimental:      "#d4a017",
    experimentalBg:    "rgba(212,160,23,0.10)",
    suppressed:        "#e74c3c",
    suppressedBg:      "rgba(231,76,60,0.10)",
  },

  // Chart-specific
  chart: {
    actual:      "#c8d8e8",
    predicted:   "#e74c3c",
    grid:        "#1a2030",
    axis:        "#4a6080",
    calibration: "#4a6080",
  },

  // Map choropleth
  map: {
    above:      "#4caf84",
    near:       "#f0c040",
    below:      "#e05252",
    suppressed: "#2a3848",
    unknown:    "#1e2a3d",
  },
} as const;

// Prediction label → hex color lookup
export const PREDICTION_COLORS: Record<string, string> = {
  "Above Normal": COLORS.forecast.above,
  "Near Normal":  COLORS.forecast.near,
  "Below Normal": COLORS.forecast.below,
};

// HSS value → tier color
export function hssToColor(hss: number): string {
  if (hss >= 0.30) return COLORS.accent.green;
  if (hss >= 0.10) return COLORS.forecast.near;
  if (hss >  0.00) return COLORS.forecast.near;
  return COLORS.forecast.below;
}
