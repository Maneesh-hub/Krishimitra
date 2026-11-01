import { useNavigate } from "react-router-dom";
import { useApp } from "../context/AppContext";
import AskPanel from "../components/AskPanel";
import { AlertList, MandiSnapshot, WeatherPanel } from "../components/Panels";
import { Card, Val } from "../components/ui";

export default function Dashboard() {
  const { t, location, crop, soil, cropName, setModal, demo } = useApp();
  const nav = useNavigate();
  const place = location ? [location.village_or_mandal, location.district, location.state].filter(Boolean).join(", ") : t("no_location");
  const s = soil?.inputs;
  return (
    <>
      <Card>
        <h1 className="text-2xl font-bold">🙏 {t("namaste")}</h1>
        <p className="mt-1">{place} {demo && <span className="badge bg-amber-light text-amber-900">{t("sample_badge")}</span>}</p>
        <p className="font-semibold">{crop?.crop_id ? `${cropName(crop.crop_id)} · ${t(`g.${crop.growth_stage || "unknown"}`)}` : t("no_crop")}</p>
        <div className="flex flex-wrap gap-2 mt-3">
          <button className="btn-ghost" onClick={() => setModal("location")}>{t("change_location")}</button>
          <button className="btn-ghost" onClick={() => setModal("crop")}>{t("change_crop")}</button></div>
      </Card>
      <Card title={t("weather")}><WeatherPanel onForecast={() => nav("/weather")} /></Card>
      <Card title={t("alerts")}><AlertList /></Card>
      <Card title={t("mandi_snapshot")}><MandiSnapshot onCompare={() => nav("/mandi")} /></Card>
      <Card title={t("soil_card")} action={<button className="btn-ghost" onClick={() => nav("/soil-crop")}>{t("add_soil")}</button>}>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {[["ph", ""], ["nitrogen", "nitrogen_unit"], ["phosphorus", "phosphorus_unit"], ["potassium", "potassium_unit"]].map(([k, u]) => (
            <div key={k} className="rounded-xl bg-cream p-3"><div className="text-sm text-gray-600">{t(k)}</div>
              <div className="font-bold">{s?.[k] != null ? `${s[k]} ${u ? s[u] || "" : ""}` : <span className="text-gray-500 font-normal">{t("not_provided")}</span>}</div></div>))}
        </div>
      </Card>
      <AskPanel />
    </>
  );
}
