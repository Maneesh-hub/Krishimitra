import { useState } from "react";
import { useApp } from "../context/AppContext";
import { api } from "../services/api";
import { useResource } from "../services/useResource";
import { GROWTH_STAGES, LOCATIONS, STATES } from "../data/locations";
import { ErrorBox } from "./ui";

const Field = ({ label, children }) => <div><label>{label}</label>{children}</div>;
const Err = ({ msg }) => (msg ? <p role="alert" className="text-red-700 font-semibold text-sm">{msg}</p> : null);
const num = (v) => (v === "" || v === null || v === undefined ? null : Number(v));

export function LocationForm({ onDone }) {
  const { t, errMsg, location, setLocation, demo } = useApp();
  const samples = useResource(api.demo, [], demo);
  const known = location && LOCATIONS.some((l) => l.state === location.state && l.district === location.district);
  const [f, setF] = useState({ state: location?.state || "", district: location?.district || "", village: location?.village_or_mandal || "",
    lat: location?.latitude ?? "", lon: location?.longitude ?? "", manual: !!location && !known && !demo });
  const [err, setErr] = useState(null);
  const set = (k, v) => setF((p) => ({ ...p, [k]: v }));

  if (demo) {
    if (samples.status === "error") return <ErrorBox message={errMsg(samples.error)} onRetry={samples.reload} />;
    return (
      <div className="space-y-3">
        <Field label={t("location")}>
          <select className="input" value={location?.sample_id || ""} onChange={(e) => {
            const l = samples.data.locations.find((x) => x.id === e.target.value);
            if (l) setLocation({ ...l, sample_id: l.id });
          }}>{samples.data?.locations.map((l) => <option key={l.id} value={l.id}>{l.village_or_mandal}, {l.district} ({t("sample_badge")})</option>)}</select>
        </Field>
        <button className="btn-primary w-full" onClick={onDone}>{t("save")}</button>
      </div>
    );
  }

  const pickState = (s) => setF((p) => ({ ...p, state: s, district: "", lat: "", lon: "" }));
  const pickDistrict = (d) => {
    const l = LOCATIONS.find((x) => x.state === f.state && x.district === d);
    setF((p) => ({ ...p, district: d, lat: l?.latitude ?? "", lon: l?.longitude ?? "" }));
  };
  const save = () => {
    if (!f.state.trim() || !f.district.trim()) return setErr({ code: "LOCATION_REQUIRED" });
    const la = num(f.lat), lo = num(f.lon);
    const bad = (la === null) !== (lo === null) || (la !== null && (isNaN(la) || isNaN(lo) || la < -90 || la > 90 || lo < -180 || lo > 180));
    if (bad) return setErr({ code: "INVALID_COORDINATES" });
    setLocation({ state: f.state.trim(), district: f.district.trim(), village_or_mandal: f.village.trim() || null, latitude: la, longitude: lo });
    onDone?.();
  };
  return (
    <div className="space-y-3">
      {!f.manual ? (<>
        <Field label={t("state")}><select className="input" value={f.state} onChange={(e) => pickState(e.target.value)}>
          <option value="">{t("select")}</option>{STATES.map((s) => <option key={s}>{s}</option>)}</select></Field>
        <Field label={t("district")}><select className="input" value={f.district} disabled={!f.state} onChange={(e) => pickDistrict(e.target.value)}>
          <option value="">{t("select")}</option>{LOCATIONS.filter((l) => l.state === f.state).map((l) => <option key={l.district}>{l.district}</option>)}</select></Field>
      </>) : (<>
        <Field label={t("state")}><input className="input" value={f.state} onChange={(e) => set("state", e.target.value)} /></Field>
        <Field label={t("district")}><input className="input" value={f.district} onChange={(e) => set("district", e.target.value)} /></Field>
      </>)}
      <button type="button" className="text-leaf underline text-sm min-h-[44px]" onClick={() => set("manual", !f.manual)}>{f.manual ? t("select") : t("other_manual")}</button>
      <Field label={t("village")}><input className="input" value={f.village} onChange={(e) => set("village", e.target.value)} /></Field>
      <div className="grid grid-cols-2 gap-3">
        <Field label={t("latitude")}><input className="input" inputMode="decimal" value={f.lat} onChange={(e) => set("lat", e.target.value)} /></Field>
        <Field label={t("longitude")}><input className="input" inputMode="decimal" value={f.lon} onChange={(e) => set("lon", e.target.value)} /></Field>
      </div>
      <p className="text-sm text-gray-600">{t("coords_note")}</p>
      <Err msg={err && errMsg(err)} />
      <div className="flex gap-2"><button className="btn-primary flex-1" onClick={save}>{t("save")}</button>
        <button className="btn-ghost" onClick={onDone}>{t("cancel")}</button></div>
    </div>
  );
}

export function CropForm({ onDone }) {
  const { t, errMsg, crop, setCrop, crops, cropName } = useApp();
  const [f, setF] = useState({ crop_id: crop?.crop_id || "", growth_stage: crop?.growth_stage || "unknown", sowing_date: crop?.sowing_date || "" });
  const [err, setErr] = useState(null);
  if (crops.status === "error") return <ErrorBox message={errMsg(crops.error)} onRetry={crops.reload} />;
  const save = () => {
    if (!f.crop_id) return setErr({ code: "CROP_REQUIRED" });
    setCrop({ crop_id: f.crop_id, crop_name: cropName(f.crop_id), growth_stage: f.growth_stage, sowing_date: f.sowing_date || null });
    onDone?.();
  };
  return (
    <div className="space-y-3">
      <Field label={t("crop")}><select className="input" value={f.crop_id} onChange={(e) => setF({ ...f, crop_id: e.target.value })}>
        <option value="">{t("select")}</option>{crops.data?.crops.map((c) => <option key={c.id} value={c.id}>{cropName(c.id)}</option>)}</select></Field>
      <Field label={t("growth_stage")}><select className="input" value={f.growth_stage} onChange={(e) => setF({ ...f, growth_stage: e.target.value })}>
        {GROWTH_STAGES.map((g) => <option key={g} value={g}>{t(`g.${g}`)}</option>)}</select></Field>
      <Field label={t("sowing_date")}><input type="date" className="input" value={f.sowing_date} onChange={(e) => setF({ ...f, sowing_date: e.target.value })} /></Field>
      <Err msg={err && errMsg(err)} />
      <div className="flex gap-2"><button className="btn-primary flex-1" onClick={save}>{t("save")}</button>
        {onDone && <button className="btn-ghost" onClick={onDone}>{t("cancel")}</button>}</div>
    </div>
  );
}

const UNITS = ["", "kg/ha", "mg/kg", "ppm", "%"];
export function SoilForm() {
  const { t, errMsg, soil, setSoil, demo } = useApp();
  const init = soil?.inputs || {};
  const [f, setF] = useState(() => ({ ph: init.ph ?? "", soil_source: init.soil_source || (demo ? "sample" : "user_entered"),
    ...Object.fromEntries(["nitrogen", "phosphorus", "potassium", "organic_carbon"].flatMap((n) => [[n, init[n] ?? ""], [n + "_unit", init[n + "_unit"] || ""]])) }));
  const [state, setState] = useState({ busy: false, error: null });
  const submit = async (e) => {
    e.preventDefault();
    const inputs = { ph: num(f.ph), soil_source: f.soil_source };
    for (const n of ["nitrogen", "phosphorus", "potassium", "organic_carbon"]) { inputs[n] = num(f[n]); inputs[n + "_unit"] = f[n + "_unit"] || null; }
    if (inputs.ph !== null && (isNaN(inputs.ph) || inputs.ph < 0 || inputs.ph > 14)) return setState({ busy: false, error: { code: "INVALID_SOIL_PH" } });
    setState({ busy: true, error: null });
    try { setSoil({ inputs, result: await api.soil(inputs) }); setState({ busy: false, error: null }); }
    catch (err) { setState({ busy: false, error: err }); }   // inputs stay in the form for retry
  };
  const row = (n) => (
    <div key={n} className="grid grid-cols-5 gap-2 items-end">
      <div className="col-span-3"><label>{t(n)}</label><input className="input" inputMode="decimal" value={f[n]} onChange={(e) => setF({ ...f, [n]: e.target.value })} /></div>
      <div className="col-span-2"><label>{t("unit")}</label><select className="input" value={f[n + "_unit"]} onChange={(e) => setF({ ...f, [n + "_unit"]: e.target.value })}>
        {UNITS.map((u) => <option key={u} value={u}>{u || "—"}</option>)}</select></div>
    </div>);
  return (
    <form onSubmit={submit} className="space-y-3">
      <Field label={`${t("ph")} (0–14)`}><input className="input" inputMode="decimal" value={f.ph} onChange={(e) => setF({ ...f, ph: e.target.value })} /></Field>
      {["nitrogen", "phosphorus", "potassium", "organic_carbon"].map(row)}
      <Field label={t("soil_source")}><select className="input" value={f.soil_source} onChange={(e) => setF({ ...f, soil_source: e.target.value })}>
        {["user_entered", "lab_report", "sample"].map((s) => <option key={s} value={s}>{t(s)}</option>)}</select></Field>
      <p className="text-sm text-gray-600">{t("soil_note")}</p>
      {state.error && <ErrorBox message={errMsg(state.error)} />}
      <button className="btn-primary w-full" disabled={state.busy}>{state.busy ? t("loading") : t("analyze")}</button>
    </form>
  );
}
