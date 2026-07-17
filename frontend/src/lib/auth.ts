import { getApiBaseUrl } from "./config";
import { getTenantFromHost } from "./tenant";

let accessToken: string | null = null;

export function setAccessToken(t: string | null) { accessToken = t; }
export function getAccessToken() { return accessToken; }

export async function login(email: string, password: string, otp?: string) {
  const tenant = getTenantFromHost();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (tenant) {
    headers["X-Tenancy-Mode"] = "header";
    headers["X-Tenant-Id"] = tenant;
  }

  const r = await fetch(`${getApiBaseUrl()}/auth/login/`, {
    method: "POST",
    credentials: "include", // set refresh cookie on server
    headers,
    body: JSON.stringify({ 
      username: email,  // Django expects username field
      password, 
      otp 
    }),
  });
  if (!r.ok) throw new Error("Login failed");
  const data = await r.json();
  setAccessToken(data.access); // short-lived JWT
  return data;
}

export async function refresh(): Promise<string> {
  const r = await fetch(`${getApiBaseUrl()}/auth/refresh/`, {
    method: "POST",
    credentials: "include",
  });
  if (!r.ok) throw new Error("Refresh failed");
  const data = await r.json();
  return data.access;
}

export async function logout() {
  await fetch(`${getApiBaseUrl()}/auth/logout/`, {
    method: "POST", credentials: "include"
  });
  setAccessToken(null);
}
