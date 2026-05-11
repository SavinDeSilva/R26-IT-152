/**
 * SO1 — Nearest police / hospitals from backend CSV datasets (haversine).
 */
import api from "./api.js";

export async function fetchNearestFacilities({ lat, lon, district, label }) {
  const params = {};
  if (lat != null && lon != null) {
    params.lat = lat;
    params.lon = lon;
    if (label) params.label = label;
  } else if (district) {
    params.district = district;
  } else {
    throw new Error("fetchNearestFacilities: pass lat/lon or district");
  }
  const { data } = await api.get("/facilities/nearest", { params });
  return data;
}
