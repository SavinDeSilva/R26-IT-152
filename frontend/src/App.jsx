import { BrowserRouter, Routes, Route, NavLink, useLocation } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Map, Shield } from "lucide-react";

import SosDashboardPage from "./pages/SosDashboardPage.jsx";
import DangerZoneMapPage from "./pages/DangerZoneMapPage.jsx";

const NAV_ITEMS = [
  { to: "/", label: "Safety", short: "SOS", icon: Shield, end: true },
  { to: "/map", label: "Risk map", short: "Map", icon: Map, end: false },
];

function BottomNav() {
  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-[600] border-t border-white/[0.08] bg-slate-950/85 backdrop-blur-2xl supports-[padding:max(0px)]:pb-[max(0.5rem,env(safe-area-inset-bottom))]"
      aria-label="Main navigation"
    >
      <div className="mx-auto flex max-w-lg">
        {NAV_ITEMS.map(({ to, label, short, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `group relative flex flex-1 flex-col items-center justify-center gap-0.5 py-3.5 text-[11px] font-medium transition-colors touch-target ${
                isActive ? "text-fuchsia-200" : "text-slate-500 hover:text-slate-300"
              }`
            }
          >
            {({ isActive }) => (
              <>
                {isActive ? (
                  <span className="absolute top-0 left-1/2 h-0.5 w-10 -translate-x-1/2 rounded-b-full bg-gradient-to-r from-fuchsia-500 to-cyan-400" />
                ) : null}
                <Icon size={22} strokeWidth={isActive ? 2.25 : 1.75} className="shrink-0" aria-hidden />
                <span className="sm:hidden">{short}</span>
                <span className="hidden sm:inline">{label}</span>
              </>
            )}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}

function AnimatedRoutes() {
  const location = useLocation();
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={location.pathname}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -6 }}
        transition={{ duration: 0.18, ease: "easeOut" }}
      >
        <Routes location={location}>
          <Route path="/" element={<SosDashboardPage />} />
          <Route path="/map" element={<DangerZoneMapPage />} />
        </Routes>
      </motion.div>
    </AnimatePresence>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-950 text-slate-100">
        <AnimatedRoutes />
        <BottomNav />
      </div>
    </BrowserRouter>
  );
}
