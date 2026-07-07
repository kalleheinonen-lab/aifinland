import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// Mock next/navigation
const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

// Mock api-client
const mockGetMfaSetup = vi.fn();
const mockConfirmMfaSetup = vi.fn();
vi.mock("@/lib/api-client", () => ({
  getMfaSetup: (...args: unknown[]) => mockGetMfaSetup(...args),
  confirmMfaSetup: (...args: unknown[]) => mockConfirmMfaSetup(...args),
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

// Auth store mock
let mockAccessToken = "test-token";
const mockRefreshAuth = vi.fn();
vi.mock("@/lib/auth-store", () => ({
  useAuthStore: (selector?: (s: { accessToken: string; refreshAuth: typeof mockRefreshAuth }) => unknown) => {
    const state = { accessToken: mockAccessToken, refreshAuth: mockRefreshAuth };
    if (selector) return selector(state);
    return state;
  },
}));

// Import after mocks
import MfaSetupPage from "./page";

// kills: QR code rendered with wrong URI, manual key not shown, backup codes not displayed, continue enabled before checkbox

describe("MfaSetupPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAccessToken = "test-token";
    mockRefreshAuth.mockResolvedValue(undefined);
  });

  // ── Introduction step ──

  it("renders the introduction step on initial load", () => {
    render(<MfaSetupPage />);

    expect(
      screen.getByText("Set Up Two-Factor Authentication")
    ).toBeInTheDocument();
    expect(
      screen.getByText(/multi-factor authentication.*is mandatory/i)
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Get Started" })).toBeInTheDocument();
  });

  it("shows step 1 of 4 indicator on intro step", () => {
    render(<MfaSetupPage />);

    expect(screen.getByLabelText("Step 1 of 4")).toBeInTheDocument();
    expect(screen.getByText("Introduction")).toBeInTheDocument();
  });

  // ── AC-1: QR code renders from provisioning URI ──

  it("AC-1: QR code renders from provisioning URI after Get Started", async () => {
    const user = userEvent.setup();
    mockGetMfaSetup.mockResolvedValueOnce({
      provisioningUri: "otpauth://totp/TestApp:user@example.com?secret=JBSWY3DPEHPK3PXP",
      secret: "JBSWY3DPEHPK3PXP",
    });

    render(<MfaSetupPage />);

    // AC-1: clicking Get Started triggers setup load and shows QR code
    await user.click(screen.getByRole("button", { name: "Get Started" }));

    await waitFor(() => {
      // QR code SVG is rendered (qrcode.react renders an SVG with role=img)
      expect(screen.getByRole("img")).toBeInTheDocument();
    });

    // Manual entry key is shown below the QR code
    expect(screen.getByText("Manual entry key:")).toBeInTheDocument();
    expect(screen.getByText("JBSWY3DPEHPK3PXP")).toBeInTheDocument();
  });

  it("shows skeleton placeholder while loading QR code", async () => {
    const user = userEvent.setup();
    // Never resolves during this test
    mockGetMfaSetup.mockReturnValue(new Promise(() => {}));

    render(<MfaSetupPage />);
    await user.click(screen.getByRole("button", { name: "Get Started" }));

    // Skeleton should be visible while loading
    expect(screen.getByRole("status", { name: "Loading QR code" })).toBeInTheDocument();
  });

  it("shows retry option on network error loading setup", async () => {
    const user = userEvent.setup();
    mockGetMfaSetup.mockRejectedValueOnce(new Error("Network error"));

    render(<MfaSetupPage />);
    await user.click(screen.getByRole("button", { name: "Get Started" }));

    await waitFor(() => {
      expect(
        screen.getByText("Failed to load MFA setup. Please try again.")
      ).toBeInTheDocument();
    });

    // Retry button should be present
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  // ── AC-2: Invalid code shows error ──

  it("AC-2: invalid TOTP code shows error message in error color", async () => {
    const user = userEvent.setup();
    mockGetMfaSetup.mockResolvedValueOnce({
      provisioningUri: "otpauth://totp/test?secret=ABC",
      secret: "ABC",
    });

    // ApiRequestError with 401 status
    const { ApiRequestError } = await import("@/lib/api-client");
    mockConfirmMfaSetup.mockRejectedValueOnce(
      new ApiRequestError("Invalid code", "INVALID_CODE", 401)
    );

    render(<MfaSetupPage />);

    // Navigate to QR step
    await user.click(screen.getByRole("button", { name: "Get Started" }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Continue" })).toBeInTheDocument()
    );

    // Navigate to verify step
    await user.click(screen.getByRole("button", { name: "Continue" }));

    // Enter invalid code
    const input = screen.getByLabelText("Verification Code");
    await user.type(input, "999999");

    // AC-2: submit triggers error display
    await user.click(screen.getByRole("button", { name: "Verify" }));

    await waitFor(() => {
      const errorAlert = screen.getByRole("alert");
      expect(errorAlert).toBeInTheDocument();
      // Error text is shown
      expect(screen.getByText("Invalid code. Please try again.")).toBeInTheDocument();
    });

    // Input is still present for retry
    expect(screen.getByLabelText("Verification Code")).toBeInTheDocument();
  });

  it("shows generic error for non-401 failures during verification", async () => {
    const user = userEvent.setup();
    mockGetMfaSetup.mockResolvedValueOnce({
      provisioningUri: "otpauth://totp/test?secret=ABC",
      secret: "ABC",
    });
    mockConfirmMfaSetup.mockRejectedValueOnce(new Error("Network error"));

    render(<MfaSetupPage />);

    await user.click(screen.getByRole("button", { name: "Get Started" }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Continue" })).toBeInTheDocument()
    );
    await user.click(screen.getByRole("button", { name: "Continue" }));

    const input = screen.getByLabelText("Verification Code");
    await user.type(input, "123456");
    await user.click(screen.getByRole("button", { name: "Verify" }));

    await waitFor(() => {
      expect(
        screen.getByText("Something went wrong. Please try again.")
      ).toBeInTheDocument();
    });
  });

  // ── AC-3: Backup codes display after confirmation ──

  it("AC-3: backup codes display after successful confirmation", async () => {
    const user = userEvent.setup();
    mockGetMfaSetup.mockResolvedValueOnce({
      provisioningUri: "otpauth://totp/test?secret=ABCDEF",
      secret: "ABCDEF",
    });
    mockConfirmMfaSetup.mockResolvedValueOnce({
      backupCodes: [
        "abc12345", "def67890", "ghi11111", "jkl22222",
        "mno33333", "pqr44444", "stu55555", "vwx66666",
        "yza77777", "bcd88888",
      ],
    });

    render(<MfaSetupPage />);

    // Navigate through intro → qrcode → verify
    await user.click(screen.getByRole("button", { name: "Get Started" }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Continue" })).toBeInTheDocument()
    );
    await user.click(screen.getByRole("button", { name: "Continue" }));

    const input = screen.getByLabelText("Verification Code");
    await user.type(input, "123456");
    await user.click(screen.getByRole("button", { name: "Verify" }));

    // AC-3: backup codes are shown after successful confirmation
    await waitFor(() => {
      expect(screen.getByText("abc12345")).toBeInTheDocument();
      expect(screen.getByText("def67890")).toBeInTheDocument();
      expect(screen.getByText("bcd88888")).toBeInTheDocument();
    });

    // Warning banner is shown
    expect(
      screen.getByText("Save these codes securely. They cannot be shown again.")
    ).toBeInTheDocument();

    // Copy-all button is present
    expect(
      screen.getByRole("button", { name: "Copy all codes" })
    ).toBeInTheDocument();
  });

  // ── AC-4: Continue button disabled until checkbox checked ──

  it("AC-4: Continue to Dashboard button is disabled until checkbox is checked", async () => {
    const user = userEvent.setup();
    mockGetMfaSetup.mockResolvedValueOnce({
      provisioningUri: "otpauth://totp/test?secret=ABCDEF",
      secret: "ABCDEF",
    });
    mockConfirmMfaSetup.mockResolvedValueOnce({
      backupCodes: ["code1", "code2", "code3", "code4", "code5"],
    });

    render(<MfaSetupPage />);

    // Navigate to backup codes step
    await user.click(screen.getByRole("button", { name: "Get Started" }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Continue" })).toBeInTheDocument()
    );
    await user.click(screen.getByRole("button", { name: "Continue" }));

    const input = screen.getByLabelText("Verification Code");
    await user.type(input, "123456");
    await user.click(screen.getByRole("button", { name: "Verify" }));

    await waitFor(() => {
      expect(screen.getByText("code1")).toBeInTheDocument();
    });

    // AC-4: Continue button is disabled before checkbox is checked
    const continueButton = screen.getByRole("button", { name: "Continue to Dashboard" });
    expect(continueButton).toBeDisabled();

    // Check the checkbox
    const checkbox = screen.getByRole("checkbox", { name: "I have saved my backup codes" });
    await user.click(checkbox);

    // AC-4: Continue button is now enabled
    expect(continueButton).not.toBeDisabled();
  });

  it("shows error message when refreshAuth fails during handleComplete", async () => {
    const user = userEvent.setup();
    mockGetMfaSetup.mockResolvedValueOnce({
      provisioningUri: "otpauth://totp/test?secret=ABCDEF",
      secret: "ABCDEF",
    });
    mockConfirmMfaSetup.mockResolvedValueOnce({
      backupCodes: ["code1", "code2"],
    });
    // AC: refreshAuth rejects → error shown, router.push NOT called
    mockRefreshAuth.mockRejectedValueOnce(new Error("Network error"));

    render(<MfaSetupPage />);

    await user.click(screen.getByRole("button", { name: "Get Started" }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Continue" })).toBeInTheDocument()
    );
    await user.click(screen.getByRole("button", { name: "Continue" }));

    const input = screen.getByLabelText("Verification Code");
    await user.type(input, "123456");
    await user.click(screen.getByRole("button", { name: "Verify" }));

    await waitFor(() =>
      expect(screen.getByText("code1")).toBeInTheDocument()
    );

    const checkbox = screen.getByRole("checkbox", { name: "I have saved my backup codes" });
    await user.click(checkbox);
    await user.click(screen.getByRole("button", { name: "Continue to Dashboard" }));

    // AC: error message is displayed to the user
    await waitFor(() => {
      expect(
        screen.getByText("Failed to complete setup. Please try again.")
      ).toBeInTheDocument();
    });

    // AC: router.push('/') is NOT called when refreshAuth fails
    expect(mockPush).not.toHaveBeenCalled();

    // AC: user remains on the backup-codes step (can retry)
    expect(screen.getByRole("button", { name: "Continue to Dashboard" })).toBeInTheDocument();
  });

  it("redirects to dashboard after completing setup", async () => {
    const user = userEvent.setup();
    mockGetMfaSetup.mockResolvedValueOnce({
      provisioningUri: "otpauth://totp/test?secret=ABCDEF",
      secret: "ABCDEF",
    });
    mockConfirmMfaSetup.mockResolvedValueOnce({
      backupCodes: ["code1", "code2"],
    });

    render(<MfaSetupPage />);

    await user.click(screen.getByRole("button", { name: "Get Started" }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Continue" })).toBeInTheDocument()
    );
    await user.click(screen.getByRole("button", { name: "Continue" }));

    const input = screen.getByLabelText("Verification Code");
    await user.type(input, "123456");
    await user.click(screen.getByRole("button", { name: "Verify" }));

    await waitFor(() =>
      expect(screen.getByText("code1")).toBeInTheDocument()
    );

    const checkbox = screen.getByRole("checkbox", { name: "I have saved my backup codes" });
    await user.click(checkbox);
    await user.click(screen.getByRole("button", { name: "Continue to Dashboard" }));

    await waitFor(() => {
      expect(mockRefreshAuth).toHaveBeenCalled();
      expect(mockPush).toHaveBeenCalledWith("/");
    });
  });
});
