import { useState } from "react";
import { Link } from "react-router-dom";
import { useApp } from "../context/AppContext";
import { api } from "../services/api";
import { EXAMPLE_QUESTIONS, LANGUAGES } from "../data/locations";
import { Card, ErrorBox, Skeleton, StatusBadge, fmtTime } from "./ui";

const urg = { low: "bg-green-100 text-green-800", medium: "bg-amber-light text-amber-900", high: "bg-red-100 text-red-800" };
const ok = (r) => (r && ["live", "cached", "sample"].includes(r.status) ? r : null);

export default function AskPanel() {
  const { t, errMsg, lang, location, crop, soil, weather, mandi, cropName, setModal } = useApp();
  const [q, setQ] = useState("");
  const [s, setS] = useState({ status: "idle" });   // idle | loading | success | partial | error (L13)
  const [retried, setRetried] = useState(false);
  const langName = LANGUAGES.find(([c]) => c === lang)?.[1];

  const submit = async (isRetry = false) => {
    if (!isRetry) setRetried(false); else setRetried(true);
    const text = q.trim();
    if (!text) return setS({ status: "error", error: { code: "QUESTION_REQUIRED" }, local: true });
    if (text.length > 1000) return setS({ status: "error", error: { code: "QUESTION_TOO_LONG" }, local: true });
    if (!location?.state || !location?.district) return setS({ status: "error", error: { code: "LOCATION_REQUIRED" }, local: true });
    if (!crop?.crop_id) return setS({ status: "error", error: { code: "CROP_REQUIRED" }, local: true });
    setS({ status: "loading" });
    const w = ok(weather.data), m = ok(mandi.data);
    try {
      const r = await api.advisory({ question: text, context: {
        language: lang, location: { state: location.state, district: location.district, village_or_mandal: location.village_or_mandal ?? null, latitude: location.latitude ?? null, longitude: location.longitude ?? null },
        crop: { crop_id: crop.crop_id, crop_name: cropName(crop.crop_id), growth_stage: crop.growth_stage || "unknown", sowing_date: crop.sowing_date || null },
        soil: soil?.inputs || null, weather: w, mandi: m ? { ...m, records: m.records.slice(0, 30) } : null } });
      setS({ status: r.status === "partial" ? "partial" : "success", data: r });
    } catch (e) { setS({ status: "error", error: e }); }   // question text stays in the box
  };
  const r = s.data;
  return (
    <div className="space-y-4">
      <Card title={t("ask_title")}>
        <div className="flex flex-wrap gap-2 text-sm mb-2">
          {crop?.crop_id ? <span className="badge bg-leaf-light text-leaf">{cropName(crop.crop_id)} · {t(`g.${crop.growth_stage || "unknown"}`)}</span> : <button className="btn-ghost" onClick={() => setModal("crop")}>{t("change_crop")}</button>}
          {!location && <button className="btn-ghost" onClick={() => setModal("location")}>{t("change_location")}</button>}
          <span className="badge bg-gray-100 text-gray-700">🌐 {langName}</span>
        </div>
        <label htmlFor="q" className="sr-only">{t("ask_title")}</label>
        <textarea id="q" rows={4} maxLength={1100} className="input" placeholder={t("ask_placeholder")} value={q} onChange={(e) => setQ(e.target.value)} />
        <div className="flex justify-between text-sm text-gray-600 mb-2"><span>{q.length}/1000</span></div>
        <div className="mb-3"><div className="text-sm font-semibold mb-1">{t("examples")}</div>
          <div className="flex flex-wrap gap-2">{EXAMPLE_QUESTIONS.map((x) => <button key={x} className="rounded-full border border-leaf text-leaf px-3 py-1.5 text-sm text-left hover:bg-leaf-light" onClick={() => setQ(x)}>{x}</button>)}</div></div>
        <button className="btn-primary w-full sm:w-auto" disabled={s.status === "loading"} onClick={() => submit(false)}>{s.status === "loading" ? t("loading") : t("get_advice")}</button>
      </Card>

      {s.status === "loading" && <Card><Skeleton rows={5} /></Card>}
      {s.status === "error" && <ErrorBox message={errMsg(s.error)} onRetry={!s.local && !retried ? () => submit(true) : undefined} />}
      {r && (
        <Card title={t("summary")} action={<div className="flex gap-2 no-print">
          {r.mode === "rule_based_demo" ? <span className="badge bg-amber text-ink">{t("ai_demo")} · {t("sample_badge")}</span> : <span className="badge bg-leaf text-white">AI</span>}
          <button className="btn-ghost !min-h-[36px] !py-1" onClick={() => window.print()}>{t("print")}</button></div>}>
          {s.status === "partial" && <p className="rounded-lg bg-amber-light p-2 text-sm mb-3">{t("partial")} {r.missing_sources.join(", ")}</p>}
          <p className="text-lg mb-4">{r.summary}</p>
          <h3 className="font-bold mb-2">{t("actions")}</h3>
          <ol className="list-decimal pl-5 space-y-3 mb-4">{r.actions.map((a, i) => (
            <li key={i}><div>{a.action} <span className={`badge ${urg[a.urgency]}`}>{t("urgency")}: {t(a.urgency)}</span></div>
              {a.reason && <div className="text-sm text-gray-700">{t("reason")}: {a.reason}</div>}</li>))}</ol>
          <h3 className="font-bold mb-1">{t("data_used")}</h3>
          <ul className="list-disc pl-5 text-sm mb-3">{r.data_used.map((d, i) => <li key={i}>{d}</li>)}</ul>
          <h3 className="font-bold mb-1">{t("sources")}</h3>
          <ul className="text-sm mb-3 space-y-1">{r.sources.map((x, i) => <li key={i} className="flex flex-wrap items-center gap-2">{x.name}{x.timestamp && <span>· {fmtTime(x.timestamp)}</span>}
            {["live", "cached", "sample", "unavailable"].includes(x.status) ? <StatusBadge status={x.status} /> : <span className="badge bg-gray-100">{x.status}</span>}</li>)}</ul>
          <h3 className="font-bold mb-1">{t("cautions")}</h3>
          <ul className="list-disc pl-5 text-sm space-y-1">{r.cautions.map((c, i) => <li key={i}>{c}</li>)}</ul>
          <p className="text-sm font-semibold mt-3 border-t pt-2">{t("advice_note")} · {fmtTime(r.generated_at)} · ID {r.request_id}</p>
        </Card>)}
    </div>
  );
}
