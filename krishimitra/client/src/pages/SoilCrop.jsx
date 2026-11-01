import { useApp } from "../context/AppContext";
import { CropForm, SoilForm } from "../components/Forms";
import { SoilResult } from "../components/Panels";
import { Card } from "../components/ui";

export default function SoilCrop() {
  const { t, soil, crop, crops, lang } = useApp();
  const ref = crops.data?.crops?.find((c) => c.id === crop?.crop_id);
  return (<>
    <Card title={t("crop")}>
      <CropForm />
      {ref && (<div className="mt-4 rounded-xl bg-cream p-3 text-sm">
        <div className="font-semibold">{ref.names?.[lang] || ref.name} · {ref.seasons.join(", ")}</div>
        <ul className="list-disc pl-5 mt-1">{ref.notes.map((n, i) => <li key={i}>{n}</li>)}</ul>
        <p className="mt-1 text-gray-600">{ref.reference_note}</p></div>)}
    </Card>
    <Card title={t("soil_card")}><SoilForm /></Card>
    {soil?.result && <Card title={t("analyze")}><SoilResult result={soil.result} /></Card>}
  </>);
}
