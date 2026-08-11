import { afterEach, describe, expect, it, vi } from "vitest";
import { checkSession, login, logout } from "./auth";

describe("auth helpers", () => {
  afterEach(() => {
    window.history.replaceState({}, "", "http://localhost:3000/");
    vi.unstubAllGlobals();
  });

  it("logs in with credentials included for the session cookie", async () => {
    window.history.replaceState({}, "", "http://localhost:3000/login?tenant=demo");
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ message: "Login successful" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(login("alice@example.com", "secret", "123456")).resolves.toEqual({ message: "Login successful" });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/auth/login/",
      expect.objectContaining({
        body: JSON.stringify({
          username: "alice@example.com",
          password: "secret",
          otp: "123456",
        }),
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          "X-Tenancy-Mode": "header",
          "X-Tenant-Id": "demo",
        },
        method: "POST",
      }),
    );
  });

  it("checks the current session via the HttpOnly cookie", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ id: 1, email: "alice@example.com" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(checkSession()).resolves.toEqual({ id: 1, email: "alice@example.com" });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/auth/me/",
      expect.objectContaining({
        credentials: "include",
        method: "GET",
      }),
    );
  });

  it("ends the tenant-scoped session on logout", async () => {
    window.history.replaceState({}, "", "http://localhost:3000/login?tenant=demo");
    const fetchMock = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal("fetch", fetchMock);

    await logout();

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/auth/logout/",
      expect.objectContaining({
        credentials: "include",
        headers: {
          "X-Tenancy-Mode": "header",
          "X-Tenant-Id": "demo",
        },
        method: "POST",
      }),
    );
  });
});
