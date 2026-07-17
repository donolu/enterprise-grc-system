import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import AuthWrapper from "./AuthWrapper";

const pushMock = vi.fn();
const refreshMock = vi.fn();
const setAccessTokenMock = vi.fn();
let pathname = "/";
let accessToken: string | null = null;

vi.mock("next/navigation", () => ({
  usePathname: () => pathname,
  useRouter: () => ({ push: pushMock }),
}));

vi.mock("@/lib/auth", () => ({
  getAccessToken: () => accessToken,
  refresh: () => refreshMock(),
  setAccessToken: (token: string | null) => setAccessTokenMock(token),
}));

describe("AuthWrapper", () => {
  beforeEach(() => {
    accessToken = null;
    pathname = "/";
    pushMock.mockClear();
    refreshMock.mockReset();
    setAccessTokenMock.mockClear();
  });

  it("refreshes the access token before rendering protected pages", async () => {
    refreshMock.mockResolvedValue("refreshed-access");

    render(
      <AuthWrapper>
        <main>Protected content</main>
      </AuthWrapper>,
    );

    await waitFor(() => {
      expect(setAccessTokenMock).toHaveBeenCalledWith("refreshed-access");
    });
    expect(await screen.findByText("Protected content")).toBeInTheDocument();
    expect(pushMock).not.toHaveBeenCalled();
  });

  it("redirects unauthenticated users away from protected pages when refresh fails", async () => {
    refreshMock.mockRejectedValue(new Error("Refresh failed"));

    render(
      <AuthWrapper>
        <main>Protected content</main>
      </AuthWrapper>,
    );

    await waitFor(() => {
      expect(pushMock).toHaveBeenCalledWith("/login");
    });
    expect(screen.queryByText("Protected content")).not.toBeInTheDocument();
  });

  it("renders public pages without requiring a token", async () => {
    pathname = "/login";

    render(
      <AuthWrapper>
        <main>Login content</main>
      </AuthWrapper>,
    );

    expect(await screen.findByText("Login content")).toBeInTheDocument();
    expect(pushMock).not.toHaveBeenCalled();
  });

  it("redirects authenticated users away from public auth pages", async () => {
    accessToken = "access-token";
    pathname = "/login";

    render(
      <AuthWrapper>
        <main>Login content</main>
      </AuthWrapper>,
    );

    await waitFor(() => {
      expect(pushMock).toHaveBeenCalledWith("/");
    });
  });
});
