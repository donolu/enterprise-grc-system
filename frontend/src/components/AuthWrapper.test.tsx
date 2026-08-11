import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import AuthWrapper from "./AuthWrapper";

const pushMock = vi.fn();
const checkSessionMock = vi.fn();
let pathname = "/";

vi.mock("next/navigation", () => ({
  usePathname: () => pathname,
  useRouter: () => ({ push: pushMock }),
}));

vi.mock("@/lib/auth", () => ({
  checkSession: () => checkSessionMock(),
}));

vi.mock("./AppLayout", () => ({
  default: ({ children }: { children: ReactNode }) => <div data-testid="app-layout">{children}</div>,
}));

describe("AuthWrapper", () => {
  beforeEach(() => {
    pathname = "/";
    pushMock.mockClear();
    checkSessionMock.mockReset();
  });

  it("checks the current session before rendering protected pages", async () => {
    checkSessionMock.mockResolvedValue({ id: 1 });

    render(
      <AuthWrapper>
        <main>Protected content</main>
      </AuthWrapper>,
    );

    await waitFor(() => {
      expect(checkSessionMock).toHaveBeenCalled();
    });
    expect(await screen.findByText("Protected content")).toBeInTheDocument();
    expect(pushMock).not.toHaveBeenCalled();
  });

  it("redirects unauthenticated users away from protected pages when the session check fails", async () => {
    checkSessionMock.mockRejectedValue(new Error("Session check failed"));

    render(
      <AuthWrapper>
        <main>Protected content</main>
      </AuthWrapper>,
    );

    await waitFor(() => {
      expect(pushMock).toHaveBeenCalledWith("/login?next=%2F");
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

  it("does not require a session check on public auth pages", async () => {
    pathname = "/login";

    render(
      <AuthWrapper>
        <main>Login content</main>
      </AuthWrapper>,
    );

    expect(checkSessionMock).not.toHaveBeenCalled();
  });
});
