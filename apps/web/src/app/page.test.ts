import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import Home from "./page";

describe("Home page", () => {
  it("renders the platform heading", () => {
    render(Home());
    // AC: page renders the platform name in an h1
    expect(
      screen.getByRole("heading", { level: 1, name: /AI Finland Matchmaking Platform/i })
    ).toBeInTheDocument();
  });
});
