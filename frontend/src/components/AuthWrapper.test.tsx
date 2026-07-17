import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import AuthWrapper from "./AuthWrapper";

const pushMock = vi.fn();
let pathname = "/";
let accessToken: string | null = null;

vi.mock("next/navigation", () => ({
  usePathname: () => pathname,
  useRouter: () => ({ push: pushMock }),
}));

vi.mock("@/lib/auth", () => ({
  getAccessToken: () => accessToken,
}));

describe("AuthWrapper", () => {
  beforeEach(() => {
    accessToken = null;
    pathname = "/";
    pushMock.mockClear();
  });

  it("redirects unauthenticated users away from protected pages", async () => {
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
