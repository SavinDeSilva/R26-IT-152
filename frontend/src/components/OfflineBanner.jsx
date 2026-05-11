import { motion } from "framer-motion";
import { CloudOff, RefreshCw } from "lucide-react";

/** Offline queue — calm, actionable strip */
export default function OfflineBanner({ online, queued, onQueue, busy }) {
  if (online) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: -4 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-amber-500/25 bg-amber-950/40 px-4 py-4 backdrop-blur-sm"
      role="status"
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5 rounded-lg bg-amber-500/15 p-2 text-amber-200">
          <CloudOff size={18} aria-hidden />
        </div>
        <div className="min-w-0 flex-1 space-y-2 text-left">
          <p className="text-sm font-medium text-amber-100">No network connection</p>
          <p className="text-xs leading-relaxed text-amber-100/75">
            Your alert can be queued and sent when you are back online (demo behaviour).
          </p>
          <button
            type="button"
            disabled={busy}
            onClick={onQueue}
            className="inline-flex min-h-[44px] w-full sm:w-auto items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-amber-600 to-rose-600 px-4 py-2.5 text-sm font-semibold text-white shadow-md transition hover:brightness-105 disabled:opacity-50"
          >
            {busy ? <RefreshCw className="animate-spin" size={16} aria-hidden /> : null}
            Queue alert for later
          </button>
          {queued ? (
            <p className="text-xs text-emerald-300/90">Saved to queue position: {queued}</p>
          ) : null}
        </div>
      </div>
    </motion.div>
  );
}
