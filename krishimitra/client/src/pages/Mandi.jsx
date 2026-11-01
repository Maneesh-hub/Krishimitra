import { useState } from "react";
import { useApp } from "../context/AppContext";
import { Comparison, MandiStatusNote, MandiTable, useMandiView } from "../components/Panels";
import { Card, Empty, ErrorBox, Skeleton } from "../components/ui";

export default function Mandi() {
  const { t, errMsg, crop, location, setModal, cropName } = useApp();
  const [draft, setDraft] = useState({ from: "", to: "", scope: "district" });
  const [applied, setApplied] = useState({ from: "", to: "", scope: "district", nonce: 0 });
  const { res, setUseSample } = useMandiView(applied);
  if (!crop?.crop_id || !location?.state) return <Card title={t("nav_mandi")}><Empty>{t("need_loc_crop")}</Empty>
    <div className="flex gap-2"><button className="btn-ghost" onClick={() => setModal("location")}>{t("change_location")}</button><button className="btn-ghost" onClick={() => setModal("crop")}>{t("change_crop")}</button></div></Card>;
  const r = res.data;
  return (<>
    <Card title={`${t("nav_mandi")} · ${cropName(crop.crop_id)}`}>
      <form className="grid grid-cols-2 sm:grid-cols-4 gap-3 items-end" onSubmit={(e) => { e.preventDefault(); setApplied({ ...draft, nonce: applied.nonce + 1 }); }}>
        <div><label>{t("from")}</label><input type="date" className="input" value={draft.from} onChange={(e) => setDraft({ ...draft, from: e.target.value })} /></div>
        <div><label>{t("to")}</label><input type="date" className="input" value={draft.to} onChange={(e) => setDraft({ ...draft, to: e.target.value })} /></div>
        <div><label>{t("location")}</label><select className="input" value={draft.scope} onChange={(e) => setDraft({ ...draft, scope: e.target.value })}>
          <option value="district">{location.district}</option><option value="state">{location.state}</option></select></div>
        <button className="btn-primary">{t("search")}</button>
      </form>
    </Card>
    {(res.status === "loading" || res.status === "idle") && <Card><Skeleton rows={4} /></Card>}
    {res.status === "error" && <ErrorBox message={errMsg(res.error)} onRetry={res.reload} />}
    {r && r.status === "unavailable" && <ErrorBox message={`${t("mandi_unavail")}. ${r.warnings[0]?.message || ""}`} onRetry={res.reload} onSample={() => setUseSample(true)} />}
    {r && r.status !== "unavailable" && (<>
      <Card title={t("nav_mandi")}><MandiStatusNote r={r} />
        {r.warnings.map((w) => <p key={w.code} className="text-sm bg-amber-light rounded-lg p-2 mb-2">{w.message}</p>)}
        {r.records.length ? <MandiTable records={r.records} /> : <Empty>{t("no_records")}</Empty>}</Card>
      {r.records.length > 0 && <Card title={t("compare_markets")}><Comparison comparison={r.comparison} /></Card>}
    </>)}
  </>);
}
