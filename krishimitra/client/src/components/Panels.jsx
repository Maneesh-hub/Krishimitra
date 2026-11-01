import { useState } from "react";
import { useApp } from "../context/AppContext";
import { api } from "../services/api";
import { useResource } from "../services/useResource";
import { Empty, ErrorBox, Skeleton, StatusBadge, Val, fmtTime } from "./ui";

const usable = (w) => w && ["live", "cached", "sample"].includes(w.status);

/** Weather data (live from Open-Meteo, or sample on request). Never shows sample values as live. */
export function useWeatherView() {
  const { weather, demo, location, hasCoords } = useApp();
  const [useSample, setUseSample] = useState(false);
  const sample = useResource(() => api.weather({ demo: true, location_id: "demo_1" }), [useSample], useSample);
  const res = useSample ? sample : weather;
  const enabled = demo || hasCoords(location);
  return { res, enabled, useSample, setUseSample, data: usable(res.data) ? res.data : null };
}

const Metric = ({ label, children }) => (
  <div className="rounded-xl bg-cream p-3"><div className="text-sm text-gray-600">{label}</div><div className="text-xl font-bold">{children}</div></div>
);

export function WeatherPanel({ onForecast }) {
  const { t, errMsg, setModal } = useApp();
  const { res, enabled, setUseSample, data } = useWeatherView();
  if (!enabled) return <div><Empty>{t("need_coords")}</Empty><button className="btn-ghost" onClick={() => setModal("location")}>{t("change_location")}</button></div>;
  if (res.status === "loading" || res.status === "idle") return <Skeleton rows={4} />;
  if (res.status === "error") return <ErrorBox message={errMsg(res.error)} onRetry={res.reload} />;
  const w = res.data;
  if (!data) return <ErrorBox message={w.warnings[0]?.message || t("unavailable")} onRetry={res.reload} onSample={() => setUseSample(true)} />;
  const c = w.current || {}, today = w.forecast?.[0] || {};
  return (
    <div>
      <div className="flex flex-wrap items-center gap-2 mb-3 text-sm">
        <StatusBadge status={w.status} />
        <span>{t("source")}: {w.source}</span><span>· {t("updated")}: {fmtTime(w.fetched_at)}</span>
        {c.time && <span>· {c.time}</span>}
      </div>
      {w.warnings.map((x) => <p key={x.code} className="text-sm text-amber-900 bg-amber-light rounded-lg p-2 mb-2">{x.message}</p>)}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <Metric label={t("temperature")}><Val v={c.temperature_c} unit="°C" /></Metric>
        <Metric label={t("humidity")}><Val v={c.humidity_pct} unit="%" /></Metric>
        <Metric label={`${t("rain")} / ${t("rain_prob")}`}><Val v={c.precipitation_mm} unit="mm" /> · <Val v={today.precipitation_probability_pct} unit="%" /></Metric>
        <Metric label={t("wind")}><Val v={c.wind_speed} unit={c.wind_speed_unit || ""} /></Metric>
      </div>
      {onForecast && <button className="btn-ghost mt-3" onClick={onForecast}>{t("view_forecast")}</button>}
    </div>
  );
}

export function AlertList() {
  const { t } = useApp();
  const { data } = useWeatherView();
  if (!data) return <Empty>{t("not_available")}</Empty>;
  return (
    <div className="space-y-2">
      {data.alerts.length === 0 && <p>{t("no_alert")}</p>}
      {data.alerts.map((a, i) => (
        <div key={i} className={`rounded-xl border p-3 ${a.severity === "caution" ? "bg-amber-light border-amber" : "bg-blue-50 border-blue-200"}`}>
          <div className="flex flex-wrap items-center gap-2"><strong>{t(`a.${a.type}`)}</strong>
            <span className="badge bg-white border">{a.severity}</span>{data.is_demo && <StatusBadge status="sample" />}</div>
          <p className="text-sm mt-1">{a.value} {a.unit} · {a.period} · {a.source}</p><p className="text-sm text-gray-700">{a.message}</p>
        </div>))}
      <p className="text-sm text-gray-600">{t("alerts_note")}</p>
    </div>
  );
}

export function ForecastList() {
  const { t } = useApp();
  const { data } = useWeatherView();
  if (!data) return null;
  return (
    <div className="overflow-x-auto"><table className="w-full text-left min-w-[480px]">
      <thead><tr className="text-sm text-gray-600"><th className="py-2">{t("date")}</th><th>{t("temperature")}</th><th>{t("rain")}</th><th>{t("rain_prob")}</th><th>{t("wind")}</th></tr></thead>
      <tbody>{data.forecast.map((d) => (
        <tr key={d.date} className="border-t">
          <td className="py-2 font-semibold">{d.date}</td>
          <td><Val v={d.temp_min_c} />–<Val v={d.temp_max_c} unit="°C" /></td>
          <td><Val v={d.precipitation_sum_mm} unit="mm" /></td>
          <td className="w-40"><div className="flex items-center gap-2"><div className="h-2 flex-1 rounded bg-gray-200"><div className="h-2 rounded bg-leaf" style={{ width: `${d.precipitation_probability_pct ?? 0}%` }} /></div><Val v={d.precipitation_probability_pct} unit="%" /></div></td>
          <td><Val v={d.wind_speed_max} unit={d.wind_speed_unit || ""} /></td>
        </tr>))}</tbody></table></div>
  );
}

/** Mandi data hook: live data via context, optional separately-labelled sample. */
export function useMandiView(filters) {
  const { mandi, crop, location, demo } = useApp();
  const [useSample, setUseSample] = useState(false);
  const custom = filters || null;
  const own = useResource(() => api.mandi({ crop: crop.crop_id, state: location.state, district: custom?.scope === "state" ? "" : location.district,
    from: custom?.from, to: custom?.to, demo: demo || useSample }), [demo, useSample, crop?.crop_id, location?.state, location?.district, custom?.from, custom?.to, custom?.scope, custom?.nonce],
    !!(custom && crop?.crop_id && location?.state));
  const useCtx = !custom && !useSample;
  const sample = useResource(() => api.mandi({ crop: crop.crop_id, state: location.state, district: location.district, demo: true }), [useSample, crop?.crop_id],
    !custom && useSample && !!crop?.crop_id);
  const res = custom ? own : useCtx ? mandi : sample;
  return { res, useSample, setUseSample };
}

export const MandiStatusNote = ({ r }) => {
  const { t } = useApp();
  return <div className="flex flex-wrap items-center gap-2 text-sm mb-2"><StatusBadge status={r.status} /><span>{t("source")}: {r.source}</span><span>· {t("updated")}: {fmtTime(r.fetched_at)}</span></div>;
};

export function MandiTable({ records }) {
  const { t } = useApp();
  return (
    <div className="overflow-x-auto"><table className="w-full text-left min-w-[560px]">
      <thead><tr className="text-sm text-gray-600"><th className="py-2">{t("market")}</th><th>{t("date")}</th><th>{t("min")}</th><th>{t("modal")}</th><th>{t("max")}</th><th>{t("unit")}</th></tr></thead>
      <tbody>{records.map((r, i) => (
        <tr key={i} className="border-t align-top">
          <td className="py-2"><div className="font-semibold">{r.market || "—"}</div><div className="text-xs text-gray-600">{[r.district, r.variety].filter(Boolean).join(" · ")}</div>
            {r.is_demo && <StatusBadge status="sample" />}</td>
          <td>{r.price_date}{r.is_stale && <div className="text-xs text-amber-900">{t("stale_note")}</div>}</td>
          <td><Val v={r.min_price} /></td><td className="font-bold"><Val v={r.modal_price} /></td><td><Val v={r.max_price} /></td>
          <td>{r.unit || <span className="text-xs text-amber-900">{t("unit_missing")}</span>}</td>
        </tr>))}</tbody></table></div>
  );
}

export function MandiSnapshot({ onCompare }) {
  const { t, errMsg, crop, location, setModal, cropName } = useApp();
  const { res, setUseSample } = useMandiView();
  if (!crop?.crop_id || !location?.state) return <div><Empty>{t("no_crop")} / {t("no_location")}</Empty><button className="btn-ghost" onClick={() => setModal(!location ? "location" : "crop")}>{t(!location ? "change_location" : "change_crop")}</button></div>;
  if (res.status === "loading" || res.status === "idle") return <Skeleton rows={3} />;
  if (res.status === "error") return <ErrorBox message={errMsg(res.error)} onRetry={res.reload} />;
  const r = res.data;
  if (r.status === "unavailable") return <div><ErrorBox message={`${t("mandi_unavail")}. ${r.warnings[0]?.message || ""}`} onRetry={res.reload} onSample={() => setUseSample(true)} /></div>;
  if (!r.records.length) return <Empty>{t("no_records")}</Empty>;
  const latest = [...r.records].sort((a, b) => b.price_date.localeCompare(a.price_date))[0];
  return (
    <div>
      <MandiStatusNote r={r} />
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div><div className="text-sm text-gray-600">{cropName(crop.crop_id)} · {latest.market || "—"} · {latest.price_date}</div>
          <div className="text-2xl font-bold"><Val v={latest.modal_price} /> <span className="text-base font-normal">{latest.unit || t("unit_missing")}</span></div>
          {latest.is_stale && <div className="text-sm text-amber-900">{t("stale_note")}</div>}</div>
        <button className="btn-ghost" onClick={onCompare}>{t("compare_markets")}</button>
      </div>
    </div>
  );
}

export function Comparison({ comparison }) {
  const { t } = useApp();
  if (!comparison?.groups?.length) return <Empty>{t("unit_missing")} / {t("comparable_only")}</Empty>;
  return (
    <div className="space-y-4">
      {comparison.groups.map((g, gi) => {
        const top = Math.max(...g.records.map((r) => r.modal_price));
        return (
          <div key={gi}><div className="font-semibold mb-1">{g.commodity} · {g.price_date} · {g.unit}</div>
            {g.records.map((r, i) => (<div key={i} className="flex items-center gap-2 mb-1">
              <span className="w-32 sm:w-40 text-sm truncate">{r.market}</span>
              <div className="flex-1 h-4 bg-gray-200 rounded"><div className="h-4 rounded bg-leaf" style={{ width: `${(r.modal_price / top) * 100}%` }} /></div>
              <span className="w-16 text-right font-semibold">{r.modal_price}</span></div>))}
          </div>);
      })}
      <p className="text-sm font-semibold">{t("comparison_note")}</p><p className="text-sm text-gray-600">{t("comparable_only")}</p>
    </div>
  );
}

export function SoilResult({ result }) {
  const { t } = useApp();
  if (!result) return null;
  return (
    <div className="space-y-2">
      <p className="text-sm font-semibold">{result.is_user_provided ? t("soil_note") : ""}</p>
      {result.items.map((i) => (
        <div key={i.parameter} className="rounded-xl border p-3">
          <div className="flex flex-wrap items-center gap-2"><strong>{t(i.parameter)}</strong><span>{i.value} {i.unit || ""}</span>
            <span className={`badge ${i.status === "interpreted" ? "bg-leaf-light text-leaf" : "bg-gray-100 text-gray-700"}`}>{i.status === "interpreted" ? `${t("interpreted")}: ${i.band.replace("_", " ")}` : t("not_interpreted")}</span></div>
          <p className="text-sm text-gray-700 mt-1">{i.note}</p></div>))}
      {result.cautions.map((c, i) => <p key={i} className="text-sm text-amber-900 bg-amber-light rounded-lg p-2">{c}</p>)}
    </div>
  );
}
