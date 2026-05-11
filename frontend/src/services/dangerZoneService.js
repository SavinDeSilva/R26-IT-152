/**
 * SO2 — Danger zone prediction & hotspots for map UI.
 */
import api from "./api.js";

export async function predictDangerZone(params) {
  const { data } = await api.get("/danger-zone/predict", { params });
  return data;
}

export async function fetchDangerHotspots() {
  const { data } = await api.get("/danger-zone/hotspots");
  return data;
}

/**
 * Risk posts from social_media_posts.csv for map markers (SO1/SO2).
 * @param {{ max_points?: number, min_risk?: number, danger_only?: boolean }} opts
 */
export async function fetchSocialRiskPoints(opts = {}) {
  const params = { land_only: "true" };
  if (opts.max_points != null) params.max_points = opts.max_points;
  if (opts.min_risk != null) params.min_risk = opts.min_risk;
  if (opts.danger_only) params.danger_only = "1";
  if (opts.land_only === false) params.land_only = "false";
  const { data } = await api.get("/danger-zone/social-risk-points", { params });
  return data;
}
