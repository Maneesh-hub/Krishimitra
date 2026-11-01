import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Weather from "./pages/Weather";
import Mandi from "./pages/Mandi";
import SoilCrop from "./pages/SoilCrop";
import Ask from "./pages/Ask";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="weather" element={<Weather />} />
        <Route path="mandi" element={<Mandi />} />
        <Route path="soil-crop" element={<SoilCrop />} />
        <Route path="ask" element={<Ask />} />
        <Route path="*" element={<Dashboard />} />
      </Route>
    </Routes>
  );
}
