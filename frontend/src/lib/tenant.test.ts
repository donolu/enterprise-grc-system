import { describe, expect, it } from "vitest";
import { getTenantFromHost } from "./tenant";

describe("getTenantFromHost", () => {
  it("extracts the first subdomain as the tenant identifier", () => {
    expect(getTenantFromHost("acme.example.com")).toBe("acme");
    expect(getTenantFromHost("tenant-a.localhost:3000")).toBe("tenant-a");
  });

  it("falls back to the tenant query parameter for local single-host usage", () => {
    window.history.replaceState({}, "", "http://localhost:3000/?tenant=demo");

    expect(getTenantFromHost()).toBe("demo");
  });

  it("returns null when no tenant signal exists", () => {
    window.history.replaceState({}, "", "http://localhost:3000/");

    expect(getTenantFromHost("localhost:3000")).toBeNull();
    expect(getTenantFromHost("example.com")).toBeNull();
    expect(getTenantFromHost()).toBeNull();
  });
});
