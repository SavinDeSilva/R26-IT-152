import { useEffect, useState } from "react";
import { reverseGeocodePlace } from "../services/geocodeService.js";

/**
 * Debounced reverse lookup for device coordinates (shows town / suburb when API is up).
 */
export function useReverseGeocode(lat, lon, enabled = true) {
  const [placeLabel, setPlaceLabel] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!enabled || lat == null || lon == null || Number.isNaN(lat) || Number.isNaN(lon)) {
      setPlaceLabel(null);
      return undefined;
    }
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      setLoading(true);
      try {
        const res = await reverseGeocodePlace(lat, lon);
        const text = res?.short_label || res?.display_name || null;
        if (!cancelled) setPlaceLabel(text);
      } catch {
        if (!cancelled) setPlaceLabel(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, 700);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [lat, lon, enabled]);

  return { placeLabel, loadingPlace: loading };
}
