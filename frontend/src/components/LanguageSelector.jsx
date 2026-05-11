import { Languages } from "lucide-react";

const OPTIONS = [
  { code: "en", label: "English" },
  { code: "si", label: "සිංහල (Sinhala)" },
  { code: "ta", label: "தமிழ் (Tamil)" },
  { code: "fr", label: "Français" },
  { code: "de", label: "Deutsch" },
  { code: "es", label: "Español" },
  { code: "zh", label: "中文" },
  { code: "ja", label: "日本語" },
  { code: "ko", label: "한국어" },
  { code: "ar", label: "العربية" },
];

export default function LanguageSelector({ value, onChange }) {
  return (
    <div className="w-full">
      <label htmlFor="sos-language" className="ui-section-label flex items-center gap-2">
        <Languages size={14} className="text-slate-500" aria-hidden />
        Preferred language
      </label>
      <select
        id="sos-language"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="ui-input cursor-pointer"
      >
        {OPTIONS.map((o) => (
          <option key={o.code} value={o.code}>
            {o.label}
          </option>
        ))}
      </select>
      <p className="mt-1.5 text-[11px] text-slate-500">Used for voice simulation and routing labels.</p>
    </div>
  );
}
