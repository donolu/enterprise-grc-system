import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AppTheme } from "@/theme";
import { EmptyState } from "./EmptyState";

const renderWithTheme = (ui: React.ReactElement) => render(<AppTheme>{ui}</AppTheme>);

describe("EmptyState", () => {
  it("renders the configured risk empty state copy", async () => {
    renderWithTheme(<EmptyState type="risks" />);

    expect(await screen.findByRole("heading", { name: "No risks identified" })).toBeInTheDocument();
    expect(
      screen.getByText("Your risk register is empty. Add risks to track and manage potential threats."),
    ).toBeInTheDocument();
  });

  it("runs primary and secondary actions", async () => {
    const primary = vi.fn();
    const secondary = vi.fn();

    renderWithTheme(
      <EmptyState
        title="No vendors"
        description="Create the first vendor profile."
        action={{ text: "Add vendor", onClick: primary }}
        secondaryAction={{ text: "Import", onClick: secondary }}
      />,
    );

    fireEvent.click(await screen.findByRole("button", { name: "Add vendor" }));
    fireEvent.click(screen.getByRole("button", { name: "Import" }));

    expect(primary).toHaveBeenCalledTimes(1);
    expect(secondary).toHaveBeenCalledTimes(1);
  });
});
