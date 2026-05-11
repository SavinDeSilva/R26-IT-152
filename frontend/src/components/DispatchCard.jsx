import { motion } from "framer-motion";
import { RadioTower, ShieldAlert } from "lucide-react";

/** SO4 — Dispatch simulation summary card. */
export default function DispatchCard({ dispatch }) {
  if (!dispatch) {
    return (
      <div className="glass-panel p-4 text-left text-slate-400 text-sm border border-dashed border-white/15">
        No active dispatch — stay alert, we are standing by. 💗
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-panel p-5 text-left space-y-3 border border-rose-400/25 shadow-glow"
    >
      <div className="flex items-center gap-2 text-rose-200 font-semibold">
        <ShieldAlert className="text-rose-300" size={18} />
        Dispatch simulation (anonymous GPS)
      </div>
      <div className="text-xs text-slate-300 space-y-1">
        <p>
          <span className="text-slate-500">Urgency:</span>{" "}
          <span className="text-amber-200">{dispatch.urgency}</span>
        </p>
        <p>
          <span className="text-slate-500">Location hint:</span>{" "}
          {dispatch.detected_location}
        </p>
        <p className="flex items-start gap-2">
          <RadioTower size={16} className="mt-0.5 text-cyan-300 shrink-0" />
          <span>
            Recipients: {(dispatch.recipients || []).join(", ")}
          </span>
        </p>
      </div>
    </motion.div>
  );
}
