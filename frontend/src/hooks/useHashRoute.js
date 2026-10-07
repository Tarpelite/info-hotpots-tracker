import { useEffect, useState } from "react";

function normalizeHash() {
  const raw = window.location.hash.replace(/^#/, "") || "/";
  const queryIndex = raw.indexOf("?");
  const rawPath = queryIndex >= 0 ? raw.slice(0, queryIndex) : raw;
  const rawSearch = queryIndex >= 0 ? raw.slice(queryIndex + 1) : "";
  const path = rawPath.startsWith("/") ? rawPath : `/${rawPath}`;
  return {
    path: path || "/",
    query: Object.fromEntries(new URLSearchParams(rawSearch)),
    search: rawSearch ? `?${rawSearch}` : ""
  };
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
