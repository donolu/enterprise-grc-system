let accessToken: string | null = null;

export function setAccessToken(t: string | null) { accessToken = t; }
export function getAccessToken() { return accessToken; }

export async function login(email: string, password: string, otp?: string) {
  const r = await fetch(`${process.env.NEXT_PUBLIC_API_BASE}/auth/login/`, {
    method: "POST",
    credentials: "include", // set refresh cookie on server
    headers: { 
      "Content-Type": "application/json",
      "Host": "demo.localhost"  // Add tenant header
    },
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
  const r = await fetch(`${process.env.NEXT_PUBLIC_API_BASE}/auth/refresh/`, {
    method: "POST",
    credentials: "include",
  });
  if (!r.ok) throw new Error("Refresh failed");
  const data = await r.json();
  return data.access;
}

export async function logout() {
  await fetch(`${process.env.NEXT_PUBLIC_API_BASE}/auth/logout/`, {
    method: "POST", credentials: "include"
  });
  setAccessToken(null);
}
