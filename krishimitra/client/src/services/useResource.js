import { useEffect, useState } from "react";

/** Loads data with explicit loading / success / error states and a manual reload(). */
export function useResource(fn, deps, enabled = true) {
  const [s, setS] = useState({ status: enabled ? "loading" : "idle", data: null, error: null });
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (!enabled) { setS({ status: "idle", data: null, error: null }); return; }
    let live = true;
    setS((p) => ({ ...p, status: "loading", error: null }));
    fn().then((d) => live && setS({ status: "success", data: d, error: null }))
        .catch((e) => live && setS({ status: "error", data: null, error: e }));
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, enabled, tick]);
  return { ...s, reload: () => setTick((x) => x + 1) };
}
