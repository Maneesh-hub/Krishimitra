import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api } from "../services/api";
import { useResource } from "../services/useResource";
import { strings } from "../i18n/strings";

const Ctx = createContext(null);
export const useApp = () => useContext(Ctx);

const load = (k, d) => { try { return JSON.parse(sessionStorage.getItem(k)) ?? d; } catch { return d; } };
const hasCoords = (l) => l && l.latitude != null && l.longitude != null;

export function AppProvider({ children }) {
  const [lang, setLang] = useState(() => localStorage.getItem("km_lang") || "en");   // remembered per browser (F1)
  const [location, setLocation] = useState(() => load("km_loc", null));               // session only (F2, F3)
  const [crop, setCrop] = useState(() => load("km_crop", null));
  const [soil, setSoil] = useState(() => load("km_soil", null));                      // {inputs, result}
  const [demo, setDemo] = useState(() => load("km_demo", false));
  const [modal, setModal] = useState(null);                                           // 'location' | 'crop' | null

  useEffect(() => { localStorage.setItem("km_lang", lang); document.documentElement.lang = lang; }, [lang]);
  useEffect(() => { sessionStorage.setItem("km_loc", JSON.stringify(location)); }, [location]);
  useEffect(() => { sessionStorage.setItem("km_crop", JSON.stringify(crop)); }, [crop]);
  useEffect(() => { sessionStorage.setItem("km_soil", JSON.stringify(soil)); }, [soil]);
  useEffect(() => { sessionStorage.setItem("km_demo", JSON.stringify(demo)); }, [demo]);

  const t = useCallback((k) => strings[lang]?.[k] ?? strings.en[k] ?? k, [lang]);
  const errMsg = useCallback((e) => (e && (strings[lang]?.[`err.${e.code}`] ?? strings.en[`err.${e.code}`])) || e?.message || "", [lang]);

  const health = useResource(api.health, [], true);
  const crops = useResource(api.crops, [], true);
  const weather = useResource(
    () => api.weather(demo ? { demo: true, location_id: location?.sample_id || "demo_1" } : { latitude: location.latitude, longitude: location.longitude }),
    [demo, location?.latitude, location?.longitude, location?.sample_id], demo || hasCoords(location));
  const mandi = useResource(
    () => api.mandi({ crop: crop.crop_id, state: location.state, district: location.district, demo }),
    [demo, crop?.crop_id, location?.state, location?.district], !!(crop?.crop_id && location?.state));

  const loadSample = useCallback(async () => {
    const d = await api.demo();
    const loc = d.locations[0];
    const prof = d.crop_profiles.find((p) => p.location_id === loc.id);
    const s = d.soil[0];
    const { id, is_demo, ...inputs } = s;
    setDemo(true);
    setLocation({ ...loc, sample_id: loc.id });
    setCrop({ crop_id: prof.crop_id, growth_stage: prof.growth_stage, sowing_date: prof.sowing_date });
    try { setSoil({ inputs, result: await api.soil(inputs) }); } catch { setSoil(null); }
  }, []);
  const exitSample = useCallback(() => { setDemo(false); setLocation(null); setCrop(null); setSoil(null); }, []);

  const cropName = useCallback((id) => {
    const c = crops.data?.crops?.find((x) => x.id === id);
    return c ? (c.names?.[lang] || c.name) : id;
  }, [crops.data, lang]);

  const value = useMemo(() => ({ lang, setLang, t, errMsg, location, setLocation, crop, setCrop, soil, setSoil, demo, setDemo, modal, setModal,
    health, crops, weather, mandi, loadSample, exitSample, cropName, hasCoords }), [lang, t, errMsg, location, crop, soil, demo, modal, health, crops, weather, mandi, loadSample, exitSample, cropName]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
