import { NavLink, Outlet } from "react-router-dom";
import { useApp } from "../context/AppContext";
import { LANGUAGES } from "../data/locations";
import { Icon, ICONS, Modal } from "./ui";
import { CropForm, LocationForm } from "./Forms";

const NAV = [["/", "nav_dashboard", "home"], ["/weather", "nav_weather", "cloud"], ["/mandi", "nav_mandi", "price"], ["/soil-crop", "nav_soil", "leaf"], ["/ask", "nav_ask", "chat"]];

function Status() {
  const { health, t } = useApp();
  const ok = health.status === "success";
  const dot = ok ? "bg-green-400" : health.status === "error" ? "bg-red-400" : "bg-gray-300";
  const sv = health.data?.services;
  const title = ok ? `Weather: ready · Mandi: ${sv.mandi.configured ? "configured" : "not configured (sample only)"} · AI: ${sv.ai.configured ? "key set" : "demo mode"}` : health.error?.message || "";
  return (
    <button onClick={health.reload} title={title} className="flex items-center gap-2 text-sm min-h-[44px] px-2" aria-label="Service status">
      <span className={`w-2.5 h-2.5 rounded-full ${dot}`} />
      <span className="hidden sm:inline">{ok ? t("server_ok") : health.status === "error" ? t("server_down") : t("loading")}</span>
      {ok && !sv.ai.configured && <span className="badge bg-amber text-ink">{t("ai_demo")}</span>}
    </button>
  );
}

export default function Layout() {
  const { t, lang, setLang, location, demo, exitSample, loadSample, modal, setModal } = useApp();
  const place = location ? [location.village_or_mandal, location.district].filter(Boolean).join(", ") : t("no_location");
  return (
    <div className="min-h-screen lg:pl-56">
      <header className="sticky top-0 z-30 bg-leaf text-white px-3 sm:px-6 py-2 flex flex-wrap items-center gap-2 lg:h-16">
        <span className="text-xl font-bold mr-auto">🌱 KrishiMitra AI</span>
        <label className="sr-only" htmlFor="lang">Language</label>
        <select id="lang" value={lang} onChange={(e) => setLang(e.target.value)} className="rounded-lg text-ink px-2 min-h-[44px]">
          {LANGUAGES.map(([c, n]) => <option key={c} value={c}>{n}</option>)}
        </select>
        <button className="flex items-center gap-1 rounded-lg bg-white/15 px-3 min-h-[44px] max-w-[48vw]" onClick={() => setModal("location")}>
          <Icon d={ICONS.pin} className="w-5 h-5 shrink-0" /><span className="truncate">{place}</span>
        </button>
        <Status />
      </header>

      <aside className="hidden lg:block fixed left-0 top-16 bottom-0 w-56 bg-white border-r p-3">
        <nav className="space-y-1">{NAV.map(([to, k, ic]) => (
          <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => `flex items-center gap-3 rounded-xl px-3 py-3 font-semibold ${isActive ? "bg-leaf text-white" : "hover:bg-leaf-light"}`}>
            <Icon d={ICONS[ic]} />{t(k)}
          </NavLink>))}
        </nav>
      </aside>

      <main className="max-w-5xl mx-auto px-3 sm:px-6 py-4 pb-28 lg:pb-8 space-y-4">
        {demo && (
          <div className="rounded-xl bg-amber-light border border-amber p-3 flex flex-wrap items-center gap-2" role="status">
            <span className="badge bg-amber text-ink">{t("sample_badge")}</span>
            <span className="font-semibold flex-1">{t("demo_banner")}</span>
            <button className="btn-ghost" onClick={exitSample}>{t("exit_sample")}</button>
          </div>
        )}
        {!demo && !location && (
          <div className="flex justify-end"><button className="btn-ghost" onClick={loadSample}>{t("load_sample")}</button></div>
        )}
        <Outlet />
        <p className="text-sm text-gray-700 border-t pt-3" role="note">⚠️ {t("disclaimer")}</p>
      </main>

      <nav className="lg:hidden fixed bottom-0 inset-x-0 z-30 bg-white border-t grid grid-cols-5">
        {NAV.map(([to, k, ic]) => (
          <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => `flex flex-col items-center justify-center gap-0.5 py-2 text-[11px] leading-tight text-center ${isActive ? "text-leaf font-bold" : "text-gray-600"}`}>
            <Icon d={ICONS[ic]} className="w-6 h-6" /><span className="px-0.5">{t(k)}</span>
          </NavLink>))}
      </nav>

      {modal === "location" && <Modal title={t("location")} onClose={() => setModal(null)}><LocationForm onDone={() => setModal(null)} /></Modal>}
      {modal === "crop" && <Modal title={t("crop")} onClose={() => setModal(null)}><CropForm onDone={() => setModal(null)} /></Modal>}
    </div>
  );
}
