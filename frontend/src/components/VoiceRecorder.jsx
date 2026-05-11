import { useRef, useState } from "react";
import { Mic, StopCircle } from "lucide-react";
import { motion } from "framer-motion";

/**
 * SO3 — Capture microphone audio; sends base64 to backend `/sos/voice`.
 */
export default function VoiceRecorder({ language, onSend, disabled }) {
  const [recording, setRecording] = useState(false);
  const [busy, setBusy] = useState(false);
  const mediaRef = useRef(null);
  const chunksRef = useRef([]);

  const start = async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      console.warn("[VoiceRecorder] getUserMedia unsupported");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      chunksRef.current = [];
      mr.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      mr.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const reader = new FileReader();
        reader.onloadend = () => {
          const res = String(reader.result || "");
          const base64 = res.includes(",") ? res.split(",")[1] : res;
          onSend?.({ audio_data: base64, language });
          setBusy(false);
        };
        reader.onerror = () => setBusy(false);
        reader.readAsDataURL(blob);
        stream.getTracks().forEach((t) => t.stop());
      };
      mr.start();
      mediaRef.current = mr;
      setRecording(true);
    } catch (e) {
      console.error("[VoiceRecorder]", e);
      setBusy(false);
    }
  };

  const stop = () => {
    if (mediaRef.current && recording) {
      setBusy(true);
      mediaRef.current.stop();
      setRecording(false);
    }
  };

  return (
    <div className="flex w-full max-w-md flex-col items-center gap-3">
      <div className="flex flex-wrap justify-center gap-3">
        {!recording ? (
          <motion.button
            type="button"
            whileTap={{ scale: 0.98 }}
            disabled={disabled || busy}
            onClick={start}
            className="ui-btn-primary gap-2 px-6 shadow-cyan-900/25"
          >
            <Mic size={18} aria-hidden />
            Record voice
          </motion.button>
        ) : (
          <motion.button
            type="button"
            whileTap={{ scale: 0.98 }}
            onClick={stop}
            className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-xl border border-rose-400/35 bg-gradient-to-r from-rose-600 to-amber-600 px-6 py-3 text-sm font-semibold text-white shadow-md transition hover:brightness-105 active:scale-[0.98]"
          >
            <StopCircle size={18} aria-hidden />
            Stop &amp; send
          </motion.button>
        )}
      </div>
      {busy ? (
        <p className="animate-pulse text-xs text-cyan-200/90">Processing audio…</p>
      ) : null}
      <p className="text-center text-[11px] leading-relaxed text-slate-500">
        Microphone access is required. Audio is sent to the server for transcription and analysis.
      </p>
    </div>
  );
}
