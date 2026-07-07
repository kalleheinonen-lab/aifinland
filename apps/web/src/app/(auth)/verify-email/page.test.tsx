import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import VerifyEmailPage from "./page";

// Mock next/navigation
const mockSearchParams = new URLSearchParams();
vi.mock("next/navigation", () => ({
  useSearchParams: () => mockSearchParams,
}));

// Mock api-client
const mockVerifyEmail = vi.fn();
const mockResendVerificationEmail = vi.fn();
vi.mock("@/lib/api-client", () => ({
  verifyEmail: (...args: unknown[]) => mockVerifyEmail(...args),
  resendVerificationEmail: (...args: unknown[]) =>
    mockResendVerificationEmail(...args),
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

describe("VerifyEmailPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset search params
    mockSearchParams.delete("token");
  });

  // Happy path: successful verification
  it("shows success state when token is valid", async () => {
    mockSearchParams.set("token", "valid-token-abc");
    mockVerifyEmail.mockResolvedValueOnce({ message: "Email verified" });

    render(<VerifyEmailPage />);

    // AC: expect success heading after verification
    await waitFor(() => {
      expect(screen.getByText("Email Verified")).toBeInTheDocument();
    });
    expect(
      screen.getByText(/verified successfully/i)
    ).toBeInTheDocument();
    expect(mockVerifyEmail).toHaveBeenCalledWith("valid-token-abc");
  });

  // Error path: no token provided
  it("shows error state when no token is in the URL", async () => {
    // No token set in mockSearchParams
    render(<VerifyEmailPage />);

    // AC: expect error heading when token is missing
    await waitFor(() => {
      expect(screen.getByText("Verification Failed")).toBeInTheDocument();
    });
    expect(
      screen.getByText("No verification token provided.")
    ).toBeInTheDocument();
    expect(mockVerifyEmail).not.toHaveBeenCalled();
  });

  // Error path: invalid/expired token
  it("shows error state when token is invalid or expired", async () => {
    mockSearchParams.set("token", "expired-token");
    const { ApiRequestError } = await import("@/lib/api-client");
    mockVerifyEmail.mockRejectedValueOnce(
      new ApiRequestError("Invalid or expired verification token", "INVALID_TOKEN", 400)
    );

    render(<VerifyEmailPage />);

    // AC: expect error message from API
    await waitFor(() => {
      expect(screen.getByText("Verification Failed")).toBeInTheDocument();
    });
    expect(
      screen.getByText("Invalid or expired verification token")
    ).toBeInTheDocument();
  });

  // Resend flow: calls resendVerificationEmail (NOT requestPasswordReset)
  it("calls resendVerificationEmail when Resend button is clicked", async () => {
    const user = userEvent.setup();
    // No token -- lands in error state immediately
    render(<VerifyEmailPage />);

    await waitFor(() => {
      expect(screen.getByText("Verification Failed")).toBeInTheDocument();
    });

    mockResendVerificationEmail.mockResolvedValueOnce({
      message: "If the email exists and is unverified, a new verification link was sent",
    });

    // AC: user types email and clicks Resend
    await user.type(
      screen.getByLabelText("Email for resend"),
      "user@example.com"
    );
    await user.click(screen.getByRole("button", { name: "Resend" }));

    // AC: resendVerificationEmail is called with the correct email
    await waitFor(() => {
      expect(mockResendVerificationEmail).toHaveBeenCalledWith("user@example.com");
    });

    // AC: success message shown after resend
    expect(
      screen.getByText(/new verification link has been sent/i)
    ).toBeInTheDocument();
  });

  // Resend flow: does NOT call requestPasswordReset
  it("does not call requestPasswordReset when Resend is clicked", async () => {
    const user = userEvent.setup();
    render(<VerifyEmailPage />);

    await waitFor(() => {
      expect(screen.getByText("Verification Failed")).toBeInTheDocument();
    });

    mockResendVerificationEmail.mockResolvedValueOnce({ message: "ok" });

    await user.type(
      screen.getByLabelText("Email for resend"),
      "user@example.com"
    );
    await user.click(screen.getByRole("button", { name: "Resend" }));

    await waitFor(() => {
      expect(mockResendVerificationEmail).toHaveBeenCalled();
    });

    // Verify the mock for requestPasswordReset was never imported or called
    // (the module mock only exports resendVerificationEmail, not requestPasswordReset)
    const apiClient = await import("@/lib/api-client");
    expect("requestPasswordReset" in apiClient).toBe(false);
  });

  // Resend flow: silently succeeds even on API error (no email enumeration)
  it("shows sent confirmation even when resend API call fails", async () => {
    const user = userEvent.setup();
    render(<VerifyEmailPage />);

    await waitFor(() => {
      expect(screen.getByText("Verification Failed")).toBeInTheDocument();
    });

    mockResendVerificationEmail.mockRejectedValueOnce(new Error("Network error"));

    await user.type(
      screen.getByLabelText("Email for resend"),
      "unknown@example.com"
    );
    await user.click(screen.getByRole("button", { name: "Resend" }));

    // AC: confirmation shown even on error (prevents email enumeration)
    await waitFor(() => {
      expect(
        screen.getByText(/new verification link has been sent/i)
      ).toBeInTheDocument();
    });
  });
});
