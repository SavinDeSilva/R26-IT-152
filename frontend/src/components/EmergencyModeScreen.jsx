import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "framer-motion";
import {
  Activity,
  Building2,
  HeartHandshake,
  MapPin,
  Navigation,
  Phone,
  Radio,
  Send,
  ShieldAlert,
  Siren,
  Users,
  X,
} from "lucide-react";

import { fetchHotelSafety } from "../services/hotelSafetyService.js";
import { fetchNearestFacilities } from "../services/facilityService.js";

/** Normalize Sri Lankan mobile for wa.me (digits only, leading 94). */
export function normalizeLKWhatsApp(input) {
  const d = String(input || "").replace(/\D/g, "");
  if (!d) return "";
  if (d.startsWith("94")) return d;
  if (d.startsWith("0")) return `94${d.slice(1)}`;
  if (d.length === 9) return `94${d}`;
  return d;
}

function mapsLink(lat, lon) {
  return `https://www.google.com/maps?q=${encodeURIComponent(`${lat},${lon}`)}`;
}

function buildEmergencyBody({
  locationLabel,
  confidencePct,
  emergencyMessage,
  situationLat,
  situationLon,
  deviceCoords,
}) {
  const mapUrl =
    situationLat != null && situationLon != null ? mapsLink(situationLat, situationLon) : "";
  const lines = [
    "🚨 SOS ALERT — Sri Lanka Safety Net (demo)",
    "",
    `📍 Place (from your message): ${locationLabel}`,
    mapUrl ? `🗺️ Situation map: ${mapUrl}` : "",
    `📊 Confidence: ${confidencePct}%`,
    "",
    `💬 Message: ${emergencyMessage || "(voice/text SOS)"}`,
  ];
  if (deviceCoords?.lat != null && deviceCoords?.lon != null) {
    lines.push(
      "",
      `📱 Live GPS (tracked): ${deviceCoords.lat.toFixed(5)}, ${deviceCoords.lon.toFixed(5)}`,
      deviceCoords.accuracy != null
        ? `📐 Accuracy ~${Math.round(deviceCoords.accuracy)} m`
        : "",
      `🗺️ GPS map: ${mapsLink(deviceCoords.lat, deviceCoords.lon)}`
    );
  }
  lines.push("", "— Sent from SOS prototype");
  return lines.filter(Boolean).join("\n");
}

/**
 * Post-detection UI — situation location from MESSAGE/SPEECH (not device GPS).
 * Actions: call 119, WhatsApp share, nearest CSV facilities, WhatsApp contact alert.
 */
export default function EmergencyModeScreen({
  open,
  onClose,
  locationLabel,
  confidencePct,
  district,
  situationLat,
  situationLon,
  locationSource,
  sourceLine,
  emergencyMessage,
  deviceCoords,
}) {
  const [safeLoading, setSafeLoading] = useState(false);
  const [safeData, setSafeData] = useState(null);
  const [safeExpanded, setSafeExpanded] = useState(false);
  const [callDone, setCallDone] = useState(false);
  const [shareDone, setShareDone] = useState(false);
  const [contactDone, setContactDone] = useState(false);
  const [continueLive, setContinueLive] = useState(false);
  const [sessionSeconds, setSessionSeconds] = useState(0);
  const [toast, setToast] = useState(null);
  const toastRef = useRef(null);
  const [facilitySnap, setFacilitySnap] = useState(null);
  const [facilitySnapLoading, setFacilitySnapLoading] = useState(false);

  const showToast = useCallback((msg) => {
    setToast(msg);
    if (toastRef.current) window.clearTimeout(toastRef.current);
    toastRef.current = window.setTimeout(() => setToast(null), 5200);
  }, []);

  useEffect(() => {
    if (!open) {
      setCallDone(false);
      setShareDone(false);
      setContactDone(false);
      setContinueLive(false);
      setSessionSeconds(0);
      setSafeData(null);
      setSafeExpanded(false);
      setToast(null);
      setFacilitySnap(null);
      setFacilitySnapLoading(false);
    }
  }, [open]);

  useEffect(() => {
    if (!open) return undefined;
    let cancelled = false;
    (async () => {
      setFacilitySnapLoading(true);
      const hasRows = (d) =>
        Boolean(d?.nearest_police?.length || d?.nearest_hospitals?.length);

      try {
        let data = null;

        if (situationLat != null && situationLon != null) {
          try {
            data = await fetchNearestFacilities({
              lat: situationLat,
              lon: situationLon,
              label: locationLabel,
            });
          } catch (e) {
            console.warn("[EmergencyMode] facilities (situation)", e);
          }
        }

        if (!hasRows(data) && deviceCoords?.lat != null && deviceCoords?.lon != null) {
          try {
            const gpsTry = await fetchNearestFacilities({
              lat: deviceCoords.lat,
              lon: deviceCoords.lon,
              label: "Live GPS position",
            });
            if (hasRows(gpsTry)) data = gpsTry;
          } catch (e) {
            console.warn("[EmergencyMode] facilities (GPS)", e);
          }
        }

        if (!hasRows(data) && district) {
          try {
            const distTry = await fetchNearestFacilities({ district });
            if (hasRows(distTry)) data = distTry;
            else if (!data) data = distTry;
          } catch (e) {
            console.warn("[EmergencyMode] facilities (district)", e);
          }
        }

        if (!cancelled) setFacilitySnap(data);
      } catch (e) {
        console.error("[EmergencyMode] facilities snap", e);
        if (!cancelled) setFacilitySnap(null);
      } finally {
        if (!cancelled) setFacilitySnapLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [open, situationLat, situationLon, locationLabel, deviceCoords?.lat, deviceCoords?.lon, district]);

  useEffect(() => {
    if (!continueLive || !open) return undefined;
    const id = setInterval(() => setSessionSeconds((s) => s + 1), 1000);
    return () => clearInterval(id);
  }, [continueLive, open]);

  const formatSession = (s) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m}:${sec.toString().padStart(2, "0")}`;
  };

  const nearestPoliceLine = () => {
    const p = facilitySnap?.nearest_police?.[0];
    if (!p) return null;
    return `${p.name} · ~${p.distance_km} km · ${p.phone || "see station"}`;
  };

  const handleCallEmergency = () => {
    setCallDone(true);
    showToast("Opening police emergency hotline (119)…");
    console.info("[EmergencyMode] tel:119");
    window.location.href = "tel:119";
  };

  const handleShareLocation = () => {
    const hasSituation = situationLat != null && situationLon != null;
    const hasDevice = deviceCoords?.lat != null && deviceCoords?.lon != null;
    if (!hasSituation && !hasDevice) {
      showToast("Turn on live GPS tracking or send an SOS with a place name first.");
      return;
    }
    const body = buildEmergencyBody({
      locationLabel,
      confidencePct,
      emergencyMessage,
      situationLat: hasSituation ? situationLat : deviceCoords.lat,
      situationLon: hasSituation ? situationLon : deviceCoords.lon,
      deviceCoords,
    });
    const url = `https://wa.me/?text=${encodeURIComponent(body)}`;
    window.open(url, "_blank", "noopener,noreferrer");
    setShareDone(true);
    showToast("WhatsApp opened — choose a contact to share your situation & map link.");
  };

  const handleNearestSafe = async () => {
    setSafeExpanded(true);
    setSafeLoading(true);
    try {
      let facilities;
      if (situationLat != null && situationLon != null) {
        facilities = await fetchNearestFacilities({
          lat: situationLat,
          lon: situationLon,
          label: locationLabel,
        });
      } else if (deviceCoords?.lat != null && deviceCoords?.lon != null) {
        facilities = await fetchNearestFacilities({
          lat: deviceCoords.lat,
          lon: deviceCoords.lon,
          label: "Live GPS position",
        });
      } else if (district) {
        facilities = await fetchNearestFacilities({ district });
      } else {
        showToast("Turn on GPS tracking or wait for a situation location from your message.");
        setSafeLoading(false);
        setSafeExpanded(false);
        return;
      }
      let hotels = [];
      try {
        const h = await fetchHotelSafety(district || "Colombo");
        hotels = h.hotels || [];
      } catch (e) {
        console.warn(e);
      }
      setSafeData({ facilities, hotels });
      showToast("Loaded nearest police, hospitals & safer hotels.");
    } catch (e) {
      console.error(e);
      setSafeData({ error: true });
    } finally {
      setSafeLoading(false);
    }
  };

  const handleContactAlert = () => {
    const phone = window.prompt(
      "WhatsApp number (e.g. 94771234567 or 0771234567):",
      ""
    );
    if (phone === null || String(phone).trim() === "") return;
    const wa = normalizeLKWhatsApp(phone);
    if (!wa || wa.length < 11) {
      showToast("Invalid number — use country code (94…).");
      return;
    }
    const body = buildEmergencyBody({
      locationLabel,
      confidencePct,
      emergencyMessage,
      situationLat,
      situationLon,
      deviceCoords,
    });
    const url = `https://wa.me/${wa}?text=${encodeURIComponent(body)}`;
    window.open(url, "_blank", "noopener,noreferrer");
    setContactDone(true);
    showToast("WhatsApp opened with your SOS message for that contact.");
  };

  const handleContinueSos = () => {
    setContinueLive(true);
    showToast("Live SOS mode ON — stay on screen; keep updating trusted contacts.");
  };

  if (typeof document === "undefined") return null;

  const policeHint = nearestPoliceLine();

  return createPortal(
    <AnimatePresence>
      {open ? (
        <motion.div
          role="alertdialog"
          aria-modal="true"
          aria-labelledby="emergency-title"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[900] flex flex-col overflow-y-auto bg-gradient-to-b from-rose-950/95 via-slate-950 to-slate-950 text-white"
        >
          <div
            className="pointer-events-none absolute inset-0 opacity-[0.08]"
            style={{
              backgroundImage:
                "radial-gradient(circle at 20% 30%, rgba(255,80,80,0.5), transparent 40%), radial-gradient(circle at 80% 20%, rgba(255,200,200,0.35), transparent 35%)",
            }}
          />

          <header className="relative z-10 mx-auto flex w-full max-w-lg items-start justify-between gap-4 px-4 pb-2 pt-7">
            <div className="flex items-center gap-3">
              <motion.div
                animate={{ scale: [1, 1.06, 1] }}
                transition={{ repeat: Infinity, duration: 1.4, ease: "easeInOut" }}
                className="rounded-2xl border border-rose-400/45 bg-rose-600/85 p-3 shadow-lg shadow-rose-900/40"
              >
                <Siren className="h-8 w-8 text-white" aria-hidden />
              </motion.div>
              <div>
                <p id="emergency-title" className="text-xl font-semibold tracking-tight text-rose-50">
                  Possible distress detected
                </p>
                <p className="mt-1 text-[13px] leading-snug text-rose-100/85">
                  Emergency assistant · primary place from your message, not device GPS
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl border border-white/15 bg-white/10 p-2.5 transition-colors hover:bg-white/18"
              aria-label="Dismiss emergency screen"
            >
              <X size={22} />
            </button>
          </header>

          <div className="relative z-10 max-w-lg mx-auto w-full px-4 pb-32 space-y-5 flex-1">
            <motion.div
              initial={{ y: 16, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              className="rounded-2xl border border-rose-500/35 bg-slate-950/50 p-5 shadow-xl shadow-rose-950/30 backdrop-blur-xl"
            >
              <div className="flex items-start gap-3">
                <MapPin className="mt-0.5 shrink-0 text-rose-300" size={22} aria-hidden />
                <div className="space-y-1 text-left">
                  <p className="text-sm font-medium text-rose-50/95">If you can, move to safety and choose an action below.</p>
                  <p className="text-lg font-semibold text-white">
                    Situation location: <span className="text-amber-200">{locationLabel}</span>
                  </p>
                  <p className="text-xs text-slate-400">
                    Source:{" "}
                    <span className="text-cyan-200">
                      {locationSource === "message_entity"
                        ? "Detected from your message (not device GPS)"
                        : locationSource === "message_text"
                          ? "Matched from words in your message"
                          : "Fallback reference point"}
                    </span>
                  </p>
                  <p className="text-sm text-slate-200">
                    Confidence: <span className="font-bold text-fuchsia-200">{confidencePct}%</span>
                  </p>
                  {sourceLine ? (
                    <p className="text-xs text-slate-400 mt-2 border-l-2 border-white/20 pl-2">{sourceLine}</p>
                  ) : null}
                </div>
              </div>

              <div className="mt-4 pt-4 border-t border-white/10 grid gap-2 text-sm text-slate-200">
                <p className="flex items-start gap-2">
                  <ShieldAlert size={16} className="text-cyan-300 shrink-0 mt-0.5" />
                  <span>
                    {facilitySnapLoading ? (
                      "Nearest police: loading…"
                    ) : policeHint ? (
                      <>
                        Nearest police: <span className="text-white">{policeHint}</span>
                      </>
                    ) : (
                      <span className="text-rose-200/90">
                        Nearest police unavailable — start the Flask API (port 5005) with datasets loaded.
                      </span>
                    )}
                  </span>
                </p>
                <p className="flex items-start gap-2">
                  <Building2 size={16} className="text-emerald-300 shrink-0 mt-0.5" />
                  <span>
                    Nearest hospital (dataset):{" "}
                    {facilitySnapLoading ? (
                      "Nearest hospital: loading…"
                    ) : facilitySnap?.nearest_hospitals?.[0] ? (
                      <>
                        {facilitySnap.nearest_hospitals[0].name} · ~
                        {facilitySnap.nearest_hospitals[0].distance_km} km
                      </>
                    ) : (
                      <span className="text-rose-200/90">
                        Hospital list unavailable — check API connection.
                      </span>
                    )}
                  </span>
                </p>
              </div>
            </motion.div>

            {continueLive ? (
              <motion.div
                initial={{ scale: 0.96, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                className="rounded-xl border border-amber-400/50 bg-amber-500/15 px-4 py-3 flex items-center justify-between gap-2"
              >
                <span className="flex items-center gap-2 text-amber-100 text-sm font-semibold">
                  <Activity className="animate-pulse" size={18} />
                  Live SOS session
                </span>
                <span className="font-mono text-amber-200">{formatSession(sessionSeconds)}</span>
              </motion.div>
            ) : null}

            <div className="space-y-3">
              <p className="text-center text-[11px] font-semibold uppercase tracking-[0.14em] text-rose-200/75">
                Next steps
              </p>

              <button
                type="button"
                onClick={handleCallEmergency}
                className="flex w-full min-h-[52px] items-center gap-3 rounded-2xl border border-red-400/35 bg-gradient-to-r from-red-600 to-rose-700 px-4 py-4 text-left font-semibold shadow-lg shadow-red-950/40 transition-all hover:brightness-110 active:scale-[0.99]"
              >
                <Phone className="shrink-0" size={22} />
                <span className="flex-1">
                  Call local emergency
                  <span className="block text-xs font-normal text-red-100/90">Police hotline 119 (Sri Lanka)</span>
                </span>
                {callDone ? <span className="text-xs bg-white/20 px-2 py-0.5 rounded-lg">Dialing</span> : null}
              </button>

              <button
                type="button"
                onClick={handleShareLocation}
                className="flex w-full min-h-[52px] items-center gap-3 rounded-2xl border border-white/15 bg-white/[0.08] px-4 py-4 text-left font-semibold backdrop-blur-md transition-all hover:bg-white/12 active:scale-[0.99]"
              >
                <Navigation className="shrink-0 text-cyan-300" size={22} />
                <span className="flex-1">
                  Share situation on WhatsApp
                  <span className="block text-xs font-normal text-slate-300">
                    Opens WhatsApp with map link (message-based location, not GPS chip)
                  </span>
                </span>
                {shareDone ? <span className="text-xs text-emerald-300 font-semibold">Sent ✓</span> : null}
              </button>

              <button
                type="button"
                onClick={handleNearestSafe}
                className="flex w-full min-h-[52px] items-center gap-3 rounded-2xl border border-white/15 bg-white/[0.08] px-4 py-4 text-left font-semibold backdrop-blur-md transition-all hover:bg-white/12 active:scale-[0.99]"
              >
                <Building2 className="shrink-0 text-emerald-300" size={22} />
                <span className="flex-1">
                  Nearest safe places
                  <span className="block text-xs font-normal text-slate-300">
                    Police & hospitals (CSV) + safer hotels
                  </span>
                </span>
              </button>

              {safeExpanded ? (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  className="rounded-xl border border-emerald-500/30 bg-emerald-950/40 overflow-hidden text-left"
                >
                  <div className="p-4 space-y-4 text-sm max-h-[70vh] overflow-y-auto">
                    {safeLoading ? (
                      <p className="text-slate-400 animate-pulse">Loading facilities…</p>
                    ) : safeData?.error ? (
                      <p className="text-rose-300 text-xs">Could not load facilities.</p>
                    ) : (
                      <>
                        <div>
                          <p className="text-cyan-200 font-semibold mb-2 flex items-center gap-2">
                            <ShieldAlert size={16} /> Police (police_stations.csv)
                          </p>
                          <ul className="space-y-2 text-xs text-slate-200">
                            {(safeData?.facilities?.nearest_police || []).map((p, i) => (
                              <li key={`p-${i}`} className="border-b border-white/10 pb-2">
                                <span className="font-medium text-white">{p.name}</span> · {p.district} · ~
                                {p.distance_km} km
                                {p.phone ? (
                                  <>
                                    {" "}
                                    ·{" "}
                                    <a href={`tel:${String(p.phone).replace(/\s/g, "")}`} className="text-cyan-300 underline">
                                      {p.phone}
                                    </a>
                                  </>
                                ) : null}
                              </li>
                            ))}
                          </ul>
                        </div>
                        <div>
                          <p className="text-emerald-200 font-semibold mb-2 flex items-center gap-2">
                            <HeartHandshake size={16} /> Hospitals (hospitals.csv)
                          </p>
                          <ul className="space-y-2 text-xs text-slate-200">
                            {(safeData?.facilities?.nearest_hospitals || []).map((h, i) => (
                              <li key={`h-${i}`} className="border-b border-white/10 pb-2">
                                <span className="font-medium text-white">{h.name}</span> · {h.district} · ~
                                {h.distance_km} km
                                {h.phone ? (
                                  <>
                                    {" "}
                                    ·{" "}
                                    <a href={`tel:${String(h.phone).replace(/\s/g, "")}`} className="text-emerald-300 underline">
                                      {h.phone}
                                    </a>
                                  </>
                                ) : null}
                              </li>
                            ))}
                          </ul>
                        </div>
                        <div>
                          <p className="text-fuchsia-200 font-semibold mb-2 flex items-center gap-2">
                            <Building2 size={16} /> Safer hotels (API)
                          </p>
                          <ul className="space-y-2 text-xs text-slate-200">
                            {(safeData?.hotels || []).slice(0, 5).map((hotel) => (
                              <li key={hotel.hotel_id} className="flex justify-between gap-2 border-b border-white/10 pb-2">
                                <span>{hotel.hotel_name}</span>
                                <span className="text-emerald-300 shrink-0">{hotel.safety_badge}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      </>
                    )}
                  </div>
                </motion.div>
              ) : null}

              <button
                type="button"
                onClick={handleContactAlert}
                className="flex w-full min-h-[52px] items-center gap-3 rounded-2xl border border-white/15 bg-white/[0.08] px-4 py-4 text-left font-semibold backdrop-blur-md transition-all hover:bg-white/12 active:scale-[0.99]"
              >
                <Users className="shrink-0 text-violet-300" size={22} />
                <span className="flex-1">
                  Send alert to contact
                  <span className="block text-xs font-normal text-slate-300">
                    Opens WhatsApp with full SOS text to the number you enter
                  </span>
                </span>
                {contactDone ? <span className="text-xs text-violet-200">Sent ✓</span> : null}
              </button>

              <button
                type="button"
                onClick={handleContinueSos}
                className="flex w-full min-h-[56px] items-center justify-center gap-3 rounded-2xl border border-white/25 bg-gradient-to-r from-fuchsia-600 via-rose-600 to-orange-500 px-4 py-5 text-base font-semibold tracking-wide shadow-xl shadow-fuchsia-950/50 transition-all hover:brightness-110 active:scale-[0.98]"
              >
                <Radio className={continueLive ? "animate-pulse" : ""} size={24} aria-hidden />
                Continue SOS session
                <Send size={20} aria-hidden />
              </button>
            </div>

            <p className="px-2 text-center text-xs leading-relaxed text-slate-500">
              The labelled place follows what you typed or said. Device GPS supplements tracking when available.
            </p>

            <button
              type="button"
              onClick={onClose}
              className="w-full py-3 text-sm text-slate-400 underline-offset-4 transition-colors hover:text-white hover:underline"
            >
              I&apos;m safe — dismiss
            </button>
          </div>

          <AnimatePresence>
            {toast ? (
              <motion.div
                initial={{ y: 40, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                exit={{ y: 20, opacity: 0 }}
                className="fixed bottom-24 left-4 right-4 z-[950] max-w-lg mx-auto rounded-xl border border-white/20 bg-slate-950/95 backdrop-blur-lg px-4 py-3 text-sm text-slate-100 shadow-xl"
              >
                {toast}
              </motion.div>
            ) : null}
          </AnimatePresence>
        </motion.div>
      ) : null}
    </AnimatePresence>,
    document.body
  );
}
