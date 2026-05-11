/**
 * Place names via backend proxy (OpenStreetMap Nominatim — see /geo/reverse).
 */
import api from "./api.js";

export async function reverseGeocodePlace(lat, lon) {
  const { data } = await api.get("/geo/reverse", { params: { lat, lon } });
  return data;
}
