import { useEffect, useState } from "react";
import { AlertTriangle, Shield } from "lucide-react";
import { predictDangerZone } from "../services/dangerZoneService.js";

/** SO2 — Live danger-zone probability panel for dashboard. */
export default function DangerZoneIndicator({ district }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await predictDangerZone({ district });
        if (!cancelled) setData(res);
      } catch (e) {
        console.error("[danger-zone]", e);
        if (!cancelled) setError("Unable to load danger zone — check API.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [district]);

  const level = data?.risk_level || "low";
  const color =
    level === "high"
      ? "text-rose-300 border-rose-400/40 shadow-glow"
      : level === "medium"
        ? "text-amber-200 border-amber-400/35"
        : "text-emerald-200 border-emerald-400/30";

  return (
    <div className={`ui-card space-y-2 border text-left ${color}`}>
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm font-semibold">
          <AlertTriangle className="text-rose-300" size={18} aria-hidden />
          Area risk signal
        </div>
        <Shield size={18} className="opacity-80 text-cyan-300" aria-hidden />
      </div>
      {loading && <p className="animate-pulse text-xs text-slate-400">Checking regional risk…</p>}
      {error && <p className="text-xs text-rose-300">{error}</p>}
      {!loading && data && (
        <>
          <p className="text-2xl font-bold capitalize">{level}</p>
          <p className="text-xs text-slate-300">
            P(danger) = {data.risk_probability} · {data.classifier}
          </p>
          <p className="text-sm text-slate-200/90">{data.warning}</p>
        </>
      )}
    </div>
  );
}
