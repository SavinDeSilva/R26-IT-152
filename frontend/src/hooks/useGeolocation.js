import { useCallback, useEffect, useRef, useState } from "react";

const GEO_OPTS = {
  enableHighAccuracy: true,
  maximumAge: 4000,
  timeout: 25000,
};

function readCoords(pos) {
  return {
    lat: pos.coords.latitude,
    lon: pos.coords.longitude,
    accuracy: pos.coords.accuracy ?? null,
    altitude: pos.coords.altitude ?? null,
    heading: pos.coords.heading ?? null,
    speed: pos.coords.speed ?? null,
    capturedAt: new Date().toISOString(),
  };
}

/**
 * SO4 — Live GPS tracking: continuously picks up current location via watchPosition.
 */
export function useGeolocation(options = {}) {
  const { autoStart = true } = options;
  const [coords, setCoords] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(Boolean(autoStart));
  const [tracking, setTracking] = useState(false);
  const watchIdRef = useRef(null);

  const clearWatch = useCallback(() => {
    if (watchIdRef.current != null && navigator.geolocation) {
      navigator.geolocation.clearWatch(watchIdRef.current);
      watchIdRef.current = null;
    }
    setTracking(false);
  }, []);

  const beginWatch = useCallback(() => {
    if (!navigator.geolocation) {
      setError("Geolocation not supported");
      setLoading(false);
      return;
    }
    clearWatch();
    setLoading(true);
    watchIdRef.current = navigator.geolocation.watchPosition(
      (pos) => {
        setCoords(readCoords(pos));
        setLoading(false);
        setError(null);
        setTracking(true);
      },
      (err) => {
        console.warn("[geo watch]", err.message);
        setError(err.message);
        setLoading(false);
      },
      GEO_OPTS
    );
    setTracking(true);
  }, [clearWatch]);

  const refresh = useCallback(() => {
    if (!navigator.geolocation) {
      setError("Geolocation not supported");
      return;
    }
    setLoading(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setCoords(readCoords(pos));
        setLoading(false);
        setError(null);
      },
      (err) => {
        console.warn("[geo]", err.message);
        setError(err.message);
        setLoading(false);
      },
      GEO_OPTS
    );
  }, []);

  useEffect(() => {
    if (!autoStart) {
      clearWatch();
      setLoading(false);
      return undefined;
    }
    beginWatch();
    return () => clearWatch();
  }, [autoStart, beginWatch, clearWatch]);

  return {
    coords,
    error,
    loading,
    tracking,
    startTracking: beginWatch,
    stopTracking: clearWatch,
    refresh,
  };
}
