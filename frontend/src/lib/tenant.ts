export function getTenantFromHost(host?: string) {
  const h = (host || (typeof window !== "undefined" ? window.location.host : "")).split(":")[0];
  const parts = h.split(".");
  if (parts.length >= 3) return parts[0];
  if (typeof window !== "undefined") {
    const t = new URLSearchParams(window.location.search).get("tenant");
    if (t) return t;
  }
  return null;
}
