import { motion } from "framer-motion";
import { HeartPulse } from "lucide-react";

export default function SOSButton({ onHoldComplete, disabled, activeAlarm }) {
  return (
    <div className="relative flex flex-col items-center gap-3">
      <motion.button
        type="button"
        disabled={disabled}
        onClick={() => onHoldComplete?.()}
        whileHover={{ scale: disabled ? 1 : 1.03 }}
        whileTap={{ scale: disabled ? 1 : 0.98 }}
        animate={activeAlarm ? { scale: [1, 1.04, 1] } : { scale: 1 }}
        transition={
          activeAlarm ? { repeat: Infinity, duration: 1.2, ease: "easeInOut" } : { type: "spring", stiffness: 280, damping: 22 }
        }
        aria-label="Send emergency SOS"
        className={`relative h-44 w-44 rounded-full text-white shadow-xl shadow-rose-900/30
          bg-gradient-to-br from-rose-600 via-fuchsia-700 to-indigo-700 border border-white/15
          disabled:pointer-events-none disabled:opacity-40`}
      >
        <span className="pointer-events-none absolute inset-0 rounded-full bg-gradient-to-tr from-white/15 to-transparent opacity-70 blur-xl" />
        <span className="relative z-10 flex flex-col items-center gap-1.5 drop-shadow-md">
          <HeartPulse size={30} className={activeAlarm ? "opacity-95" : "opacity-90"} aria-hidden />
          <span className="text-2xl font-bold tracking-[0.25em]">SOS</span>
        </span>
      </motion.button>
      <p className="max-w-[18rem] text-center text-xs leading-relaxed text-slate-400">
        Opens your phone to the nearest police contact when available, then sends your SOS for analysis.
      </p>
    </div>
  );
}
