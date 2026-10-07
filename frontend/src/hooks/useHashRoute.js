import { useEffect, useState } from "react";

function normalizeHash() {
  const raw = window.location.hash.replace(/^#/, "") || "/";
  const path = raw.startsWith("/") ? raw : `/${raw}`;
  return { path };
}

export function useHashRoute() {
  const [route, setRoute] = useState(() => normalizeHash());

  useEffect(() => {
    const handleChange = () => setRoute(normalizeHash());
    window.addEventListener("hashchange", handleChange);
    return () => window.removeEventListener("hashchange", handleChange);
  }, []);

  return route;
}
