import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Building2, LocateFixed, MapPin, Shield, Sparkles, Timer } from "lucide-react";

import SOSButton from "../components/SOSButton.jsx";
import VoiceRecorder from "../components/VoiceRecorder.jsx";
import DangerZoneIndicator from "../components/DangerZoneIndicator.jsx";
import OfflineBanner from "../components/OfflineBanner.jsx";
import DispatchCard from "../components/DispatchCard.jsx";
import ConfidenceMeter from "../components/ConfidenceMeter.jsx";
import LanguageSelector from "../components/LanguageSelector.jsx";
import EmergencyModeScreen from "../components/EmergencyModeScreen.jsx";

import { useGeolocation } from "../hooks/useGeolocation.js";
import { useReverseGeocode } from "../hooks/useReverseGeocode.js";
import { useNetworkStatus } from "../hooks/useNetworkStatus.js";
import { useCountdown } from "../hooks/useCountdown.js";

import { sendTextSos, sendVoiceSos, queueOfflineSos, fetchOfflineStatus } from "../services/sosService.js";
import { fetchHotelSafety } from "../services/hotelSafetyService.js";
import { fetchNearestFacilities } from "../services/facilityService.js";

/** Pack browser GPS for SOS API (live-tracked coordinates). */
function packDeviceLocation(coords) {
  if (coords == null || coords.lat == null || coords.lon == null) return undefined;
  return {
    lat: coords.lat,
    lon: coords.lon,
    accuracy_m: coords.accuracy ?? undefined,
    captured_at: coords.capturedAt,
  };
}

const KNOWN_DISTRICTS = [
  "Colombo",
  "Kandy",
  "Galle",
  "Negombo",
  "Jaffna",
  "Trincomalee",
  "Batticaloa",
  "Anuradhapura",
];

/**
 * Map API payload → emergency overlay. Situation place comes from backend NLP + district
 * matching (message/speech), not the phone GPS chip.
 */
function buildEmergencyContext(apiResponse, fallbackDistrict) {
  const cls = apiResponse?.classification;
  const dispatch = apiResponse?.dispatch;
  const distress = Boolean(cls?.is_distress) || Boolean(dispatch);
  if (!distress) return null;

  const sit = apiResponse?.situation_location || {};
  const lat =
    typeof sit.latitude === "number"
      ? sit.latitude
      : typeof dispatch?.situation_coordinates?.latitude === "number"
        ? dispatch.situation_coordinates.latitude
        : null;
  const lon =
    typeof sit.longitude === "number"
      ? sit.longitude
      : typeof dispatch?.situation_coordinates?.longitude === "number"
        ? dispatch.situation_coordinates.longitude
        : null;

  const locationLabel = sit.label || dispatch?.detected_location || fallbackDistrict;

  const confRaw = typeof cls?.confidence === "number" ? cls.confidence : NaN;
  const confidencePct = Number.isFinite(confRaw)
    ? Math.round(Math.min(100, Math.max(0, confRaw * 100)))
    : 72;

  let sourceLine = "";
  if (apiResponse?.input_text) {
    const t = String(apiResponse.input_text);
    sourceLine = `“${t.slice(0, 140)}${t.length > 140 ? "…" : ""}”`;
  } else if (apiResponse?.transcription?.text) {
    const t = apiResponse.transcription.text;
    sourceLine = `Voice: “${t.slice(0, 140)}${t.length > 140 ? "…" : ""}”`;
  }

  const labelForMatch = String(locationLabel || "").replace(/ \(GPS\)$/, "");
  const districtForHotels =
    KNOWN_DISTRICTS.find((d) => labelForMatch.toLowerCase().includes(d.toLowerCase())) || fallbackDistrict;

  let emergencyMessage = "";
  if (apiResponse?.input_text) emergencyMessage = String(apiResponse.input_text);
  else if (apiResponse?.transcription?.text) emergencyMessage = String(apiResponse.transcription.text);

  return {
    locationLabel,
    confidencePct,
    district: districtForHotels,
    sourceLine,
    situationLat: lat,
    situationLon: lon,
    locationSource: sit.source || "dispatch_coordinates",
    emergencyMessage,
  };
}

/** SO3 + SO4 + SO5 — Primary SOS cockpit; distress → full-screen emergency action assistant. */
export default function SosDashboardPage() {
  const [language, setLanguage] = useState("en");
  const [text, setText] = useState("");
  const [district, setDistrict] = useState("Colombo");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [alarm, setAlarm] = useState(false);
  const [hotelPreview, setHotelPreview] = useState(null);
  const [hotelPreviewLoading, setHotelPreviewLoading] = useState(false);
  const [offlineQueuedNote, setOfflineQueuedNote] = useState(null);

  const [emergencyOpen, setEmergencyOpen] = useState(false);
  const [emergencyCtx, setEmergencyCtx] = useState(null);
  const [dashboardFacilities, setDashboardFacilities] = useState(null);
  const [dashboardFacilitiesLoading, setDashboardFacilitiesLoading] = useState(false);
  const [facilityLoadError, setFacilityLoadError] = useState(null);

  const online = useNetworkStatus();
  const {
    coords,
    error: geoErr,
    refresh: refreshGeo,
    tracking,
    startTracking,
    stopTracking,
    loading: geoLoading,
  } = useGeolocation({ autoStart: true });
  const { placeLabel: gpsPlaceName, loadingPlace: gpsPlaceLoading } = useReverseGeocode(
    coords?.lat,
    coords?.lon,
    Boolean(coords?.lat != null && coords?.lon != null)
  );
  const countdownActive = Boolean(response?.dispatch);
  const timer = useCountdown(180, countdownActive);

  const dispatchPayload = useMemo(() => {
    if (!response) return null;
    return response.dispatch || response.classification?.dispatch || null;
  }, [response]);

  const confidenceValue = useMemo(() => {
    const c = response?.classification?.confidence;
    if (typeof c === "number") return c;
    return 0.35;
  }, [response]);

  /** District for hotel API — prefers place name from last SOS response when it mentions an area. */
  const inferredHotelDistrict = useMemo(() => {
    const lbl = response?.situation_location?.label || "";
    const fromSituation = KNOWN_DISTRICTS.find((d) => lbl.toLowerCase().includes(d.toLowerCase()));
    return fromSituation || district;
  }, [response?.situation_location?.label, district]);

  const situationRef = response?.situation_location;

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setHotelPreviewLoading(true);
      try {
        const data = await fetchHotelSafety(inferredHotelDistrict);
        if (!cancelled) setHotelPreview(data);
      } catch (e) {
        console.error(e);
        if (!cancelled) setHotelPreview({ error: true });
      } finally {
        if (!cancelled) setHotelPreviewLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [inferredHotelDistrict]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setDashboardFacilitiesLoading(true);
      setFacilityLoadError(null);
      try {
        let data;
        if (situationRef?.latitude != null && situationRef?.longitude != null) {
          data = await fetchNearestFacilities({
            lat: situationRef.latitude,
            lon: situationRef.longitude,
            label: situationRef.label,
          });
        } else if (coords?.lat != null && coords?.lon != null) {
          data = await fetchNearestFacilities({
            lat: coords.lat,
            lon: coords.lon,
            label: "Live GPS position",
          });
        } else {
          data = await fetchNearestFacilities({ district });
        }
        if (!cancelled) setDashboardFacilities(data);
      } catch (e) {
        console.error(e);
        const msg =
          e?.response?.data?.detail ||
          e?.response?.data?.error ||
          e?.message ||
          "Could not reach the API.";
        if (!cancelled) {
          setDashboardFacilities(null);
          setFacilityLoadError(String(msg));
        }
      } finally {
        if (!cancelled) setDashboardFacilitiesLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [
    district,
    situationRef?.latitude,
    situationRef?.longitude,
    situationRef?.label,
    coords?.lat,
    coords?.lon,
  ]);

  const applyDetectionResult = (data) => {
    setResponse(data);
    const ctx = buildEmergencyContext(data, district);
    if (ctx) {
      setEmergencyCtx(ctx);
      setEmergencyOpen(true);
      setAlarm(true);
      window.setTimeout(() => setAlarm(false), 14000);
    } else {
      setEmergencyOpen(false);
      setEmergencyCtx(null);
    }
  };

  const fireTextSos = async (bodyText) => {
    setLoading(true);
    setResponse(null);
    try {
      console.info("[SOS] text dispatch", { language });
      const data = await sendTextSos({
        text: bodyText,
        language,
        device_location: packDeviceLocation(coords),
      });
      applyDetectionResult(data);
    } catch (e) {
      console.error(e);
      setResponse({ error: e?.message || "Request failed" });
      setEmergencyOpen(false);
      setEmergencyCtx(null);
    } finally {
      setLoading(false);
    }
  };

  const handleGiantSos = async () => {
    const body = text.trim() || "Help me please I am in danger near Colombo — need police assistance.";
    try {
      let fac;
      if (coords?.lat != null && coords?.lon != null) {
        fac = await fetchNearestFacilities({
          lat: coords.lat,
          lon: coords.lon,
          label: "Live GPS position",
        });
      } else {
        fac = await fetchNearestFacilities({ district });
      }
      const raw = fac?.nearest_police?.[0]?.phone;
      if (raw) {
        const tel = String(raw).replace(/\s/g, "");
        window.location.href = `tel:${tel}`;
      }
    } catch (e) {
      console.warn("[SOS] Could not load nearest police for dial — still sending SOS.", e);
    }
    await fireTextSos(body);
  };

  const handleVoice = async (payload) => {
    setLoading(true);
    setResponse(null);
    try {
      console.info("[SOS] voice dispatch");
      const data = await sendVoiceSos({
        ...payload,
        device_location: packDeviceLocation(coords),
      });
      applyDetectionResult(data);
    } catch (e) {
      console.error(e);
      setResponse({ error: e?.message || "Voice SOS failed" });
      setEmergencyOpen(false);
      setEmergencyCtx(null);
    } finally {
      setLoading(false);
    }
  };

  const handleOfflineQueue = async () => {
    setLoading(true);
    try {
      const loc = coords || { lat: 6.9271, lon: 79.8612, note: "fallback Colombo centroid (demo)" };
      const res = await queueOfflineSos({
        tourist_id: "anonymous-web-client",
        location: { lat: loc.lat, lon: loc.lon },
        distress_type: text ? "custom_text_pending" : "silent_ping",
      });
      setOfflineQueuedNote(res.position || res.queue_id);
      await fetchOfflineStatus();
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const loadHotels = async () => {
    setHotelPreviewLoading(true);
    try {
      const data = await fetchHotelSafety(inferredHotelDistrict);
      setHotelPreview(data);
    } catch (e) {
      console.error(e);
      setHotelPreview({ error: true });
    } finally {
      setHotelPreviewLoading(false);
    }
  };

  const dismissEmergency = () => {
    setEmergencyOpen(false);
    setEmergencyCtx(null);
    setAlarm(false);
  };

  const facilitiesFromLabel = useMemo(() => {
    if (situationRef?.label) return `your last SOS situation (${situationRef.label})`;
    if (coords?.lat != null && coords?.lon != null) return "your live GPS position";
    return `district centre (${district})`;
  }, [situationRef?.label, coords?.lat, coords?.lon, district]);

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900/90 to-slate-950 pb-32">
      {emergencyCtx ? (
        <EmergencyModeScreen
          open={emergencyOpen}
          onClose={dismissEmergency}
          locationLabel={emergencyCtx.locationLabel}
          confidencePct={emergencyCtx.confidencePct}
          district={emergencyCtx.district}
          situationLat={emergencyCtx.situationLat}
          situationLon={emergencyCtx.situationLon}
          locationSource={emergencyCtx.locationSource}
          sourceLine={emergencyCtx.sourceLine}
          emergencyMessage={emergencyCtx.emergencyMessage}
          deviceCoords={coords}
        />
      ) : null}

      <main className="app-shell pt-8 sm:pt-10" aria-busy={loading}>
        <motion.header
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-10 text-center"
        >
          <p className="mb-3 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-4 py-1.5 text-[11px] font-medium uppercase tracking-[0.2em] text-fuchsia-200/95">
            <Sparkles size={14} className="text-fuchsia-300" aria-hidden />
            SOS · Sri Lanka
          </p>
          <h1 className="ui-heading-page text-gradient">You are seen. You are supported.</h1>
          <p className="ui-muted mx-auto mt-3 max-w-lg">
            When something feels wrong, send a signal. We analyze your words, estimate the situation place, and guide
            practical next steps—not just a warning.
          </p>
        </motion.header>

        <div className="space-y-6">
          <OfflineBanner online={online} queued={offlineQueuedNote} busy={loading} onQueue={handleOfflineQueue} />

          <section className="ui-card" aria-labelledby="lang-heading">
            <h2 id="lang-heading" className="sr-only">
              Language
            </h2>
            <LanguageSelector value={language} onChange={setLanguage} />
          </section>

          <section className="ui-card border-cyan-500/20" aria-labelledby="gps-heading">
            <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
              <div>
                <span className="ui-section-label" id="gps-heading">
                  Live device location
                </span>
                <p className="flex items-center gap-2 text-sm font-medium text-slate-200">
                  <LocateFixed
                    size={18}
                    className={
                      tracking ? "text-cyan-400 drop-shadow-[0_0_10px_rgba(34,211,238,0.45)]" : "text-slate-500"
                    }
                    aria-hidden
                  />
                  GPS tracking
                </p>
              </div>
              <span
                className={`rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-wide ${
                  tracking
                    ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-200"
                    : "border-slate-600 text-slate-500"
                }`}
              >
                {tracking ? "Active" : "Paused"}
              </span>
            </div>
            <p className="mb-4 text-[13px] leading-relaxed text-slate-500">
              Continuous updates while this tab is open help responders follow movement. Allow location when your browser
              asks.
            </p>
            <div className="mb-4 flex flex-wrap gap-2">
              <button type="button" onClick={startTracking} className="ui-btn-secondary text-[13px]">
                Resume
              </button>
              <button type="button" onClick={stopTracking} className="ui-btn-secondary text-[13px]">
                Pause
              </button>
              <button type="button" onClick={refreshGeo} className="ui-btn-secondary text-[13px]">
                Refresh once
              </button>
            </div>
            {coords ? (
              <div className="rounded-xl border border-white/[0.07] bg-slate-950/60 p-4 font-mono text-xs text-slate-200">
                {gpsPlaceLoading ? (
                  <p className="mb-2 font-sans text-[13px] text-slate-400">Looking up place name…</p>
                ) : gpsPlaceName ? (
                  <p className="mb-3 font-sans text-sm font-medium leading-snug text-cyan-100">{gpsPlaceName}</p>
                ) : null}
                <p>
                  <span className="text-slate-500">Lat</span> {coords.lat.toFixed(6)}{" "}
                  <span className="text-slate-500">Lon</span> {coords.lon.toFixed(6)}
                </p>
                {coords.accuracy != null ? (
                  <p className="mt-1 text-cyan-200/85">Accuracy ±{Math.round(coords.accuracy)} m</p>
                ) : null}
                {coords.capturedAt ? (
                  <p className="mt-1 text-[10px] text-slate-500">Updated {new Date(coords.capturedAt).toLocaleString()}</p>
                ) : null}
                {!gpsPlaceLoading && !gpsPlaceName ? (
                  <p className="mt-2 font-sans text-[11px] text-slate-500">
                    Place name uses the demo API — ensure Flask is running for lookup.
                  </p>
                ) : null}
              </div>
            ) : (
              <p className="text-sm text-amber-200/90">
                {geoLoading ? "Getting your position…" : geoErr || "Allow location access when prompted."}
              </p>
            )}
          </section>

          <section className="ui-card" aria-labelledby="message-heading">
            <label htmlFor="sos-message" className="ui-section-label">
              What should we know?
            </label>
            <p id="message-heading" className="sr-only">
              Optional message before SOS
            </p>
            <textarea
              id="sos-message"
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={4}
              placeholder='Example: “I need help near Galle Fort” — distress triggers the emergency assistant.'
              className="ui-input mb-4 resize-y placeholder:text-slate-600"
            />
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <button
                type="button"
                disabled={loading}
                onClick={() => fireTextSos(text.trim() || "Emergency — please assist.")}
                className="ui-btn-primary shrink-0"
              >
                Send text SOS
              </button>
              <p className="ui-muted max-w-md text-left text-[13px] sm:text-right">
                Requests include your live GPS when tracking is on. The situation place on the map comes from your words,
                not the GPS chip alone.
              </p>
            </div>
            {geoErr ? <p className="mt-3 text-left text-xs text-amber-200/90">Location: {geoErr}</p> : null}
          </section>

          <section className="flex flex-col items-center gap-8 py-2" aria-label="Quick SOS">
            <SOSButton onHoldComplete={handleGiantSos} disabled={loading} activeAlarm={alarm} />
            <VoiceRecorder language={language} onSend={handleVoice} disabled={loading} />
          </section>

          <section className="ui-card border-cyan-500/15" aria-labelledby="facilities-heading">
            <span className="ui-section-label" id="facilities-heading">
              Nearest help
            </span>
            <p className="mb-4 flex items-center gap-2 text-sm font-medium text-slate-200">
              <Shield size={16} className="text-cyan-400" aria-hidden />
              Police &amp; hospital (by distance)
            </p>
            <p className="mb-4 text-[13px] leading-relaxed text-slate-500">
              Ranked from {facilitiesFromLabel}. Data comes from bundled facility lists used by the demo API.
            </p>
            {dashboardFacilitiesLoading ? (
              <p className="animate-pulse text-sm text-slate-400">Loading nearest facilities…</p>
            ) : facilityLoadError ? (
              <div className="space-y-2 text-sm text-rose-300">
                <p>{facilityLoadError}</p>
                <p className="text-[13px] text-slate-500">
                  Start the Flask app from <code className="text-slate-400">backend/</code> (port 5005) and refresh this page.
                </p>
              </div>
            ) : dashboardFacilities?.nearest_police?.[0] || dashboardFacilities?.nearest_hospitals?.[0] ? (
              <div className="grid gap-4 sm:grid-cols-2">
                {dashboardFacilities?.nearest_police?.[0] ? (
                  <div className="rounded-xl border border-white/[0.07] bg-slate-950/45 p-4">
                    <p className="mb-2 flex items-center gap-1.5 text-xs font-medium text-cyan-300">
                      <MapPin size={12} aria-hidden />
                      Police
                    </p>
                    <p className="font-medium text-white">{dashboardFacilities.nearest_police[0].name}</p>
                    <p className="mt-1 text-xs text-slate-400">
                      ~{dashboardFacilities.nearest_police[0].distance_km} km · {dashboardFacilities.nearest_police[0].district}
                    </p>
                    {dashboardFacilities.nearest_police[0].phone ? (
                      <a
                        href={`tel:${String(dashboardFacilities.nearest_police[0].phone).replace(/\s/g, "")}`}
                        className="mt-2 inline-block text-sm text-cyan-300 underline-offset-2 hover:underline"
                      >
                        {dashboardFacilities.nearest_police[0].phone}
                      </a>
                    ) : null}
                  </div>
                ) : null}
                {dashboardFacilities?.nearest_hospitals?.[0] ? (
                  <div className="rounded-xl border border-white/[0.07] bg-slate-950/45 p-4">
                    <p className="mb-2 flex items-center gap-1.5 text-xs font-medium text-emerald-300">
                      <Building2 size={12} aria-hidden />
                      Hospital
                    </p>
                    <p className="font-medium text-white">{dashboardFacilities.nearest_hospitals[0].name}</p>
                    <p className="mt-1 text-xs text-slate-400">
                      ~{dashboardFacilities.nearest_hospitals[0].distance_km} km · {dashboardFacilities.nearest_hospitals[0].district}
                    </p>
                    {dashboardFacilities.nearest_hospitals[0].phone ? (
                      <a
                        href={`tel:${String(dashboardFacilities.nearest_hospitals[0].phone).replace(/\s/g, "")}`}
                        className="mt-2 inline-block text-sm text-emerald-300 underline-offset-2 hover:underline"
                      >
                        {dashboardFacilities.nearest_hospitals[0].phone}
                      </a>
                    ) : null}
                  </div>
                ) : null}
              </div>
            ) : (
              <div className="space-y-2 text-sm">
                {dashboardFacilities?.warning ? (
                  <p className="text-amber-200">{dashboardFacilities.warning}</p>
                ) : null}
                <p className="text-rose-300/95">
                  No facilities returned. Confirm CSV files exist under backend/datasets and the API is running on port 5005.
                </p>
              </div>
            )}
          </section>

          <div className="grid gap-4 md:grid-cols-2">
            <DangerZoneIndicator district={district} />
            <section className="ui-card flex flex-col gap-3 text-left">
              <span className="ui-section-label">Hotels near detected area</span>
              <p className="text-[13px] leading-relaxed text-slate-500">
                Loaded automatically for{" "}
                <strong className="font-medium text-slate-300">{inferredHotelDistrict}</strong>
                {response?.situation_location?.label ? (
                  <span className="text-slate-500"> (from your last situation label when it names a district).</span>
                ) : (
                  <span className="text-slate-500"> (matches your district selector until an SOS narrows the place).</span>
                )}
              </p>
              <label htmlFor="district-select" className="sr-only">
                District
              </label>
              <select
                id="district-select"
                value={district}
                onChange={(e) => setDistrict(e.target.value)}
                className="ui-input cursor-pointer py-2.5 text-[13px]"
              >
                {KNOWN_DISTRICTS.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
              <button type="button" onClick={loadHotels} disabled={hotelPreviewLoading} className="ui-btn-secondary w-full text-[13px]">
                {hotelPreviewLoading ? "Refreshing…" : "Refresh hotel list"}
              </button>
              {hotelPreviewLoading && !hotelPreview?.hotels ? (
                <p className="text-xs text-slate-400 animate-pulse">Loading hotels…</p>
              ) : null}
              {hotelPreview?.hotels?.length ? (
                <ul className="space-y-2 text-xs text-slate-200">
                  {hotelPreview.hotels.slice(0, 5).map((h) => (
                    <li key={h.hotel_id} className="flex justify-between gap-2 border-b border-white/[0.06] pb-2 last:border-0">
                      <span>{h.hotel_name}</span>
                      <span className="shrink-0 text-emerald-300">{h.safety_badge}</span>
                    </li>
                  ))}
                </ul>
              ) : null}
              {hotelPreview?.error ? <p className="text-xs text-rose-300">Hotel feed unavailable.</p> : null}
            </section>
          </div>

          <section className="ui-card border-fuchsia-500/25">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <ConfidenceMeter value={confidenceValue} label="Distress confidence (model)" />
              {countdownActive ? (
                <div className="flex items-center gap-2 text-xs text-cyan-200">
                  <Timer size={16} aria-hidden />
                  Window · {timer}s
                </div>
              ) : (
                <span className="text-xs text-slate-500">Guardian timer · 180s when dispatch is active</span>
              )}
            </div>
            <DispatchCard dispatch={dispatchPayload} />
            {response?.error ? (
              <p className="mt-4 text-left text-sm text-rose-300">{String(response.error)}</p>
            ) : null}
            <details className="divider-soft mt-6 pt-2 text-left">
              <summary className="cursor-pointer text-xs text-slate-500 hover:text-slate-300">
                Technical details (API response)
              </summary>
              {response ? (
                <pre className="mt-3 max-h-64 overflow-auto rounded-xl border border-white/[0.06] bg-slate-950/70 p-3 text-[11px] whitespace-pre-wrap text-slate-400">
                  {JSON.stringify(response, null, 2)}
                </pre>
              ) : (
                <p className="mt-3 text-xs text-slate-500">No response yet.</p>
              )}
            </details>
          </section>
        </div>
      </main>
    </div>
  );
}
