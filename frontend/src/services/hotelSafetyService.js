/**
 * SO1 — Hotel safety listings per district.
 */
import api from "./api.js";

export async function fetchHotelSafety(district) {
  const path = `/hotel-safety/${encodeURIComponent(district)}`;
  const { data } = await api.get(path);
  return data;
}

export async function fetchModelStats() {
  const { data } = await api.get("/model-stats");
  return data;
}
