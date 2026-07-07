import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import RegisterPage from "./page";

// Mock api-client
const mockRegister = vi.fn();
vi.mock("@/lib/api-client", () => ({
  register: (...args: unknown[]) => mockRegister(...args),
  ApiRequestError: class ApiRequestError extends Error {
    code: string;
    status: number;
    constructor(message: string, code: string, status: number) {
      super(message);
      this.name = "ApiRequestError";
      this.code = code;
      this.status = status;
    }
  },
}));

describe("RegisterPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // AC-1: form renders with all required fields
  it("AC-1: renders registration form with all fields", () => {
    render(<RegisterPage />);

    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Display Name")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(screen.getByLabelText("Confirm Password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create Account" })).toBeInTheDocument();
  });

  // AC-2: client-side validation rejects weak passwords
  it("AC-2: shows validation error for password shorter than 12 characters", async () => {
    const user = userEvent.setup();
    render(<RegisterPage />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Display Name"), "Test User");
    await user.type(screen.getByLabelText("Password"), "Short1!");
    await user.type(screen.getByLabelText("Confirm Password"), "Short1!");
    await user.click(screen.getByRole("button", { name: "Create Account" }));

    // AC-2: expect validation error for short password
    await waitFor(() => {
      expect(screen.getByText("Password must be at least 12 characters")).toBeInTheDocument();
    });
    expect(mockRegister).not.toHaveBeenCalled();
  });

  // AC-3: validation requires uppercase, lowercase, digit, symbol
  it("AC-3: shows validation error for password missing uppercase", async () => {
    const user = userEvent.setup();
    render(<RegisterPage />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Display Name"), "Test User");
    await user.type(screen.getByLabelText("Password"), "alllowercase1!");
    await user.type(screen.getByLabelText("Confirm Password"), "alllowercase1!");
    await user.click(screen.getByRole("button", { name: "Create Account" }));

    await waitFor(() => {
      expect(screen.getByText("Password must contain an uppercase letter")).toBeInTheDocument();
    });
  });

  // AC-4: password mismatch shows error
  it("AC-4: shows error when passwords do not match", async () => {
    const user = userEvent.setup();
    render(<RegisterPage />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Display Name"), "Test User");
    await user.type(screen.getByLabelText("Password"), "ValidPass123!!");
    await user.type(screen.getByLabelText("Confirm Password"), "DifferentPass1!");
    await user.click(screen.getByRole("button", { name: "Create Account" }));

    await waitFor(() => {
      expect(screen.getByText("Passwords do not match")).toBeInTheDocument();
    });
  });

  // AC-5: successful registration shows success message
  it("AC-5: shows check-your-email message on successful registration", async () => {
    const user = userEvent.setup();
    mockRegister.mockResolvedValueOnce({ message: "Registration successful" });

    render(<RegisterPage />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Display Name"), "Test User");
    await user.type(screen.getByLabelText("Password"), "ValidPass123!!");
    await user.type(screen.getByLabelText("Confirm Password"), "ValidPass123!!");
    await user.click(screen.getByRole("button", { name: "Create Account" }));

    await waitFor(() => {
      expect(screen.getByText("Check Your Email")).toBeInTheDocument();
      expect(
        screen.getByText(/sent a verification link/)
      ).toBeInTheDocument();
    });
  });

  // AC-6: duplicate email (409) shows specific error
  it("AC-6: shows duplicate email error on 409 response", async () => {
    const user = userEvent.setup();
    const { ApiRequestError } = await import("@/lib/api-client");
    mockRegister.mockRejectedValueOnce(
      new ApiRequestError("Email already exists", "CONFLICT", 409)
    );

    render(<RegisterPage />);

    await user.type(screen.getByLabelText("Email"), "existing@example.com");
    await user.type(screen.getByLabelText("Display Name"), "Test User");
    await user.type(screen.getByLabelText("Password"), "ValidPass123!!");
    await user.type(screen.getByLabelText("Confirm Password"), "ValidPass123!!");
    await user.click(screen.getByRole("button", { name: "Create Account" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
      expect(screen.getByText("An account with this email already exists.")).toBeInTheDocument();
    });
  });

  // AC-7: accessibility - all inputs have labels
  it("AC-7: all form inputs have associated labels for accessibility", () => {
    render(<RegisterPage />);

    expect(screen.getByLabelText("Email")).toHaveAttribute("id", "email");
    expect(screen.getByLabelText("Display Name")).toHaveAttribute("id", "displayName");
    expect(screen.getByLabelText("Password")).toHaveAttribute("id", "password");
    expect(screen.getByLabelText("Confirm Password")).toHaveAttribute("id", "confirmPassword");
  });

  // AC-8: loading state disables button
  it("AC-8: disables submit button during loading", async () => {
    const user = userEvent.setup();
    mockRegister.mockReturnValueOnce(new Promise(() => {}));

    render(<RegisterPage />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Display Name"), "Test User");
    await user.type(screen.getByLabelText("Password"), "ValidPass123!!");
    await user.type(screen.getByLabelText("Confirm Password"), "ValidPass123!!");
    await user.click(screen.getByRole("button", { name: "Create Account" }));

    await waitFor(() => {
      const button = screen.getByRole("button");
      expect(button).toBeDisabled();
    });
  });
});
