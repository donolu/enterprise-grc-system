import { getApiBaseUrl } from "./config";
import { getTenantFromHost } from "./tenant";

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
  return r.json();
}

export async function checkSession() {
  const tenant = getTenantFromHost();
  const headers: Record<string, string> = {};
  if (tenant) {
    headers["X-Tenancy-Mode"] = "header";
    headers["X-Tenant-Id"] = tenant;
  }

  const r = await fetch(`${getApiBaseUrl()}/auth/me/`, {
    method: "GET",
    credentials: "include",
    headers,
  });
  if (!r.ok) throw new Error("Session check failed");
  return r.json();
}

export async function logout() {
  const tenant = getTenantFromHost();
  const headers: Record<string, string> = {};
  if (tenant) {
    headers["X-Tenancy-Mode"] = "header";
    headers["X-Tenant-Id"] = tenant;
  }

  const response = await fetch(`${getApiBaseUrl()}/auth/logout/`, {
    method: "POST",
    credentials: "include",
    headers,
  });
  if (!response.ok) throw new Error("Logout failed");
}
