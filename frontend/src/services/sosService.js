/**
 * SO3 + SO4 — SOS voice/text API helpers.
 */
import api from "./api.js";

export async function sendTextSos(payload) {
  const { data } = await api.post("/sos/text", payload);
  return data;
}

/**
 * @param {object} payload — include optional device_location: { lat, lon, accuracy?, captured_at? }
 */
export async function sendVoiceSos(payload) {
  const { data } = await api.post("/sos/voice", payload);
  return data;
}

export async function queueOfflineSos(payload) {
  const { data } = await api.post("/offline/queue", payload);
  return data;
}

export async function fetchOfflineStatus() {
  const { data } = await api.get("/offline/status");
  return data;
}
