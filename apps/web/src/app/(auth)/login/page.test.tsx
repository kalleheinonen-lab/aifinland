import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import LoginPage from "./page";

// Mock next/navigation
const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

// Mock api-client
const mockLogin = vi.fn();
vi.mock("@/lib/api-client", () => ({
  login: (...args: unknown[]) => mockLogin(...args),
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

// Mock auth-store
const mockSetTokens = vi.fn();
vi.mock("@/lib/auth-store", () => ({
  useAuthStore: (selector: (s: Record<string, unknown>) => unknown) =>
    selector({ setTokens: mockSetTokens }),
}));

describe("LoginPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // AC-1: form renders with email and password fields and submit button
  it("AC-1: renders login form with email, password fields and submit button", () => {
    render(<LoginPage />);

    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign In" })).toBeInTheDocument();
  });

  // AC-2: form validation requires email and password
  it("AC-2: email and password inputs are required", () => {
    render(<LoginPage />);

    const emailInput = screen.getByLabelText("Email");
    const passwordInput = screen.getByLabelText("Password");

    expect(emailInput).toBeRequired();
    expect(passwordInput).toBeRequired();
  });

  // AC-3: successful login calls setTokens and redirects
  it("AC-3: successful login stores tokens and redirects to home", async () => {
    const user = userEvent.setup();
    const loginResponse = {
      accessToken: "test-token",
      user: { sub: "user-1", org: "org-1", roles: ["user"] },
    };
    mockLogin.mockResolvedValueOnce(loginResponse);

    render(<LoginPage />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Password"), "password123!");
    await user.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith({
        email: "test@example.com",
        password: "password123!",
      });
    });

    await waitFor(() => {
      expect(mockSetTokens).toHaveBeenCalledWith(loginResponse);
      expect(mockPush).toHaveBeenCalledWith("/");
    });
  });

  // AC-4: error state shows error message with icon
  it("AC-4: displays error message when login fails", async () => {
    const user = userEvent.setup();
    const { ApiRequestError } = await import("@/lib/api-client");
    mockLogin.mockRejectedValueOnce(
      new ApiRequestError("Invalid credentials", "INVALID_CREDENTIALS", 401)
    );

    render(<LoginPage />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Password"), "wrongpassword");
    await user.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
      expect(screen.getByText("Invalid credentials")).toBeInTheDocument();
    });
  });

  // AC-5: loading state disables button
  it("AC-5: disables submit button during loading", async () => {
    const user = userEvent.setup();
    // Never resolves to keep loading state
    mockLogin.mockReturnValueOnce(new Promise(() => {}));

    render(<LoginPage />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Password"), "password123!");
    await user.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => {
      const button = screen.getByRole("button");
      expect(button).toBeDisabled();
    });
  });

  // AC-6: MFA required redirects to /login/mfa
  it("AC-6: redirects to MFA page when MFA is required", async () => {
    const user = userEvent.setup();
    mockLogin.mockResolvedValueOnce({
      mfaRequired: true,
      mfaToken: "mfa-token-123",
      accessToken: "",
      user: null,
    });

    render(<LoginPage />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Password"), "password123!");
    await user.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/login/mfa?mfaToken=mfa-token-123");
    });
  });

  // AC-7: accessibility - labels are associated with inputs
  it("AC-7: all form inputs have associated labels", () => {
    render(<LoginPage />);

    const emailInput = screen.getByLabelText("Email");
    const passwordInput = screen.getByLabelText("Password");

    expect(emailInput).toHaveAttribute("id", "email");
    expect(passwordInput).toHaveAttribute("id", "password");
  });

  // AC-8: navigation links present
  it("AC-8: shows links to register and password reset", () => {
    render(<LoginPage />);

    expect(screen.getByText("Create an account")).toHaveAttribute("href", "/register");
    expect(screen.getByText("Forgot password?")).toHaveAttribute("href", "/password-reset");
  });
});
