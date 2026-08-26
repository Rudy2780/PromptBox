import { render, screen } from "@testing-library/react";
import { describe, test, expect } from "vitest";

import Chains from "../pages/Chains";
import CostForecast from "../pages/CostForecast";

/*
 * These pages are layout skeletons for features that do not exist. The point
 * of these tests is that they stay empty: the reference designs are full of
 * numbers and step names, and none of that data is real.
 */

describe("Chains placeholder", () => {
  test("states the real status", () => {
    render(<Chains />);
    expect(screen.getByText("Prompt chains are in development.")).toBeInTheDocument();
  });

  test("shows no invented pipeline steps or variables", () => {
    const { container } = render(<Chains />);

    for (const invented of [/extract topics/i, /summarize each/i, /draft report/i, /article_url/i, /running/i, /waiting/i]) {
      expect(screen.queryByText(invented)).not.toBeInTheDocument();
    }
    // No digits anywhere -- no step counts, no "Prompt 1".
    expect(container.textContent).not.toMatch(/\d/);
  });
});

describe("Cost forecast placeholder", () => {
  test("states the real status", () => {
    render(<CostForecast />);
    expect(screen.getByText("Cost tracking is in development.")).toBeInTheDocument();
  });

  test("shows no invented figures", () => {
    const { container } = render(<CostForecast />);

    // Token usage is discarded by every provider adapter, so there is nothing
    // to total. Any currency symbol or digit here would be fabricated.
    expect(container.textContent).not.toMatch(/\$/);
    expect(container.textContent).not.toMatch(/\d/);
    expect(screen.queryByText(/total spent/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/on track/i)).not.toBeInTheDocument();
  });
});
