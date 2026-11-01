import { useApp } from "../context/AppContext";
import { AlertList, ForecastList, WeatherPanel } from "../components/Panels";
import { Card } from "../components/ui";

export default function Weather() {
  const { t } = useApp();
  return (<>
    <Card title={t("weather")}><WeatherPanel /></Card>
    <Card title={t("alerts")}><AlertList /></Card>
    <Card title={t("forecast")}><ForecastList /></Card>
  </>);
}
