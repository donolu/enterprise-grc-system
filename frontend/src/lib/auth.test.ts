import { afterEach, describe, expect, it, vi } from "vitest";
import { getAccessToken, login, logout, refresh, setAccessToken } from "./auth";

describe("auth helpers", () => {
  afterEach(() => {
    setAccessToken(null);
    window.history.replaceState({}, "", "http://localhost:3000/");
    vi.unstubAllGlobals();
  });

  it("stores access tokens only in module memory", () => {
    setAccessToken("access-token");

    expect(getAccessToken()).toBe("access-token");

    setAccessToken(null);

    expect(getAccessToken()).toBeNull();
  });

  it("logs in with credentials included and stores the returned access token", async () => {
    window.history.replaceState({}, "", "http://localhost:3000/login?tenant=demo");
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ access: "new-access" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(login("alice@example.com", "secret", "123456")).resolves.toEqual({
      access: "new-access",
    });

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
    expect(getAccessToken()).toBe("new-access");
  });

  it("refreshes via the HttpOnly cookie request path", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ access: "refreshed-access" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(refresh()).resolves.toBe("refreshed-access");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/auth/refresh/",
      expect.objectContaining({
        credentials: "include",
        method: "POST",
      }),
    );
  });

  it("clears the in-memory token on logout", async () => {
    setAccessToken("old-token");
    const fetchMock = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal("fetch", fetchMock);

    await logout();

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/auth/logout/",
      expect.objectContaining({
        credentials: "include",
        method: "POST",
      }),
    );
    expect(getAccessToken()).toBeNull();
  });
});
