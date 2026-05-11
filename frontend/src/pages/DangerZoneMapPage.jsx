import { useEffect, useMemo, useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import { motion } from "framer-motion";
import { Database, Flame } from "lucide-react";

import { fetchSocialRiskPoints } from "../services/dangerZoneService.js";

/** SO2 — Map of risk signals from social_media_posts.csv (dataset-driven). */
export default function DangerZoneMapPage() {
  const [meta, setMeta] = useState(null);
  const [points, setPoints] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchSocialRiskPoints({ max_points: 12000, min_risk: 0.55 });
        if (!cancelled) {
          setPoints(data.points || []);
          setMeta({
            totalMatching: data.total_matching_in_dataset,
            returned: data.returned,
            capped: data.capped,
            filter: data.filter,
            droppedOffshore: data.dropped_offshore_bbox ?? 0,
          });
        }
      } catch (e) {
        console.error(e);
        if (!cancelled) {
          setError(
            "Cannot load risk points. Generate datasets and run the Flask API (GET /danger-zone/social-risk-points)."
          );
          setPoints([]);
          setMeta(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const colorForRisk = useMemo(
    () => (risk) => {
      const p = Number(risk) || 0;
      if (p >= 0.75) return { color: "#fb7185", fill: "#fb7185" };
      if (p >= 0.6) return { color: "#fb923c", fill: "#fb923c" };
      return { color: "#eab308", fill: "#eab308" };
    },
    []
  );

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 pb-32 text-white">
      <div className="app-shell space-y-6 pt-8 sm:pt-10">
        <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="space-y-3 text-center">
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-cyan-200/90">
            Dataset-backed risk map
          </p>
          <h2 className="flex items-center justify-center gap-2 text-2xl font-semibold tracking-tight text-gradient sm:text-3xl">
            <Flame className="text-orange-300" size={28} aria-hidden />
            Social signals on the map
          </h2>
          <p className="mx-auto max-w-xl text-sm leading-relaxed text-slate-400">
            Points use synthetic coordinates near district centres; offshore outliers are removed so markers stay over Sri
            Lanka land (demo bbox filter).
          </p>
          {meta ? (
            <>
              <p className="flex flex-wrap items-center justify-center gap-2 text-xs text-slate-500">
                <Database size={14} className="shrink-0 text-fuchsia-400" aria-hidden />
                <span>
                  Showing <strong className="font-medium text-slate-300">{meta.returned?.toLocaleString()}</strong> of{" "}
                  <strong className="font-medium text-slate-300">{meta.totalMatching?.toLocaleString()}</strong> matching
                  posts
                  {meta.capped ? (
                    <span className="text-amber-200/90">
                      {" "}
                      (capped for performance — adjust max_points in the client request if needed)
                    </span>
                  ) : null}
                </span>
              </p>
              {meta.droppedOffshore > 0 ? (
                <p className="text-xs text-slate-500">
                  Removed {meta.droppedOffshore.toLocaleString()} offshore/out-of-range coordinates from this sample (land
                  filter).
                </p>
              ) : null}
            </>
          ) : null}
        </motion.div>

        <div className="glass-panel overflow-hidden border border-white/[0.08]">
          <div className="relative h-[calc(100vh-260px)] min-h-[420px] w-full">
            {loading && (
              <div className="absolute inset-0 z-[500] flex items-center justify-center bg-slate-950/75 text-sm text-slate-200 backdrop-blur-sm">
                <span className="animate-pulse">Loading coordinates…</span>
              </div>
            )}
            <MapContainer center={[7.8731, 80.7718]} zoom={7} scrollWheelZoom className="z-0 h-full w-full">
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a>'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              {points.map((p) => {
                const palette = colorForRisk(p.risk_score);
                const r = 3 + Math.min(14, (p.risk_score || 0) * 18);
                return (
                  <CircleMarker
                    key={p.post_id}
                    center={[p.latitude, p.longitude]}
                    radius={r}
                    pathOptions={{
                      color: palette.color,
                      fillColor: palette.fill,
                      fillOpacity: 0.42,
                      weight: 1,
                    }}
                  >
                    <Popup className="max-w-xs text-slate-900">
                      <div className="space-y-1 text-xs">
                        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Area / district</p>
                        <p className="text-sm font-bold text-slate-900">{p.district}</p>
                        <p>
                          <span className="text-slate-600">Risk:</span> {p.risk_score}{" "}
                          <span className="text-slate-600">· DZ:</span> {p.danger_zone}
                        </p>
                        <p>
                          <span className="text-slate-600">Incident:</span> {p.incident_type}
                        </p>
                        <p className="text-[10px] text-slate-600">{p.post_id}</p>
                        <p className="mt-1 border-t pt-1 text-[10px]">{p.text_snippet}</p>
                      </div>
                    </Popup>
                  </CircleMarker>
                );
              })}
            </MapContainer>
          </div>
          <div className="flex flex-wrap justify-center gap-x-6 gap-y-2 border-t border-white/[0.07] bg-slate-950/70 px-4 py-3 text-[11px] text-slate-400">
            <span className="flex items-center gap-2">
              <span className="h-3 w-3 shrink-0 rounded-full bg-rose-400" /> High (≥ 0.75)
            </span>
            <span className="flex items-center gap-2">
              <span className="h-3 w-3 shrink-0 rounded-full bg-orange-400" /> Medium (0.60–0.74)
            </span>
            <span className="flex items-center gap-2">
              <span className="h-3 w-3 shrink-0 rounded-full bg-yellow-400" /> Lower (still flagged)
            </span>
          </div>
        </div>

        {error ? <p className="text-center text-sm text-rose-300">{error}</p> : null}
      </div>
    </div>
  );
}
