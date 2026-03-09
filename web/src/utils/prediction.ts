// ── Prediction label / color utilities ───────────────────────────
import type { PredictionLabel, AnomalyStatus } from "@/types/forecast";
import { COLORS } from "@/constants/colors";

export function predictionColor(prediction: PredictionLabel | null): string {
  if (!prediction) return COLORS.map.unknown;
  switch (prediction) {
    case "Above Normal": return COLORS.forecast.above;
    case "Near Normal":  return COLORS.forecast.near;
    case "Below Normal": return COLORS.forecast.below;
  }
}

export function predictionMapColor(prediction: PredictionLabel | null): string {
  if (!prediction) return COLORS.map.unknown;
  switch (prediction) {
    case "Above Normal": return COLORS.map.above;
    case "Near Normal":  return COLORS.map.near;
    case "Below Normal": return COLORS.map.below;
  }
}

export function predictionBgClass(prediction: PredictionLabel | null): string {
  switch (prediction) {
    case "Above Normal": return "bg-forecast-above-bg border-forecast-above";
    case "Near Normal":  return "bg-forecast-near-bg border-forecast-near";
    case "Below Normal": return "bg-forecast-below-bg border-forecast-below";
    default:             return "bg-background-elevated border-background-border";
  }
}

export function predictionTextClass(prediction: PredictionLabel | null): string {
  switch (prediction) {
    case "Above Normal": return "text-forecast-above";
    case "Near Normal":  return "text-forecast-near";
    case "Below Normal": return "text-forecast-below";
    default:             return "text-text-muted";
  }
}

export function anomalyToText(status: AnomalyStatus): string {
  switch (status) {
    case "Below Normal": return "Rainfall deficit vs baseline";
    case "Near Normal":  return "Near baseline";
    case "Above Normal": return "Rainfall surplus vs baseline";
  }
}

// Given prob_below, prob_near, prob_above — which class dominates?
export function dominantPrediction(
  probBelow: number,
  probNear: number,
  probAbove: number
): PredictionLabel {
  const max = Math.max(probBelow, probNear, probAbove);
  if (max === probAbove) return "Above Normal";
  if (max === probBelow) return "Below Normal";
  return "Near Normal";
}
