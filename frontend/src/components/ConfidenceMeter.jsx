import { motion } from "framer-motion";

/** Confidence visualization for distress / model outputs (SO3). */
export default function ConfidenceMeter({ value, label = "Confidence" }) {
  const pct = Math.round(Math.min(1, Math.max(0, value)) * 100);
  return (
    <div className="w-full space-y-2">
      <div className="flex justify-between text-xs text-slate-400">
        <span>{label}</span>
        <span className="text-fuchsia-200 font-semibold">{pct}%</span>
      </div>
      <div className="h-3 rounded-full bg-slate-800 overflow-hidden border border-white/10">
        <motion.div
          className="h-full rounded-full bg-gradient-to-r from-cyan-400 via-fuchsia-500 to-rose-500"
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ type: "spring", stiffness: 120, damping: 18 }}
        />
      </div>
    </div>
  );
}
