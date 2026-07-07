import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// Mock next/navigation
const mockPush = vi.fn();
const mockPathname = vi.fn(() => "/");
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
  usePathname: () => mockPathname(),
}));

// Mock api-client
const mockRefreshToken = vi.fn();
const mockLogout = vi.fn();
const mockGetMfaSetup = vi.fn();
const mockConfirmMfaSetup = vi.fn();
vi.mock("@/lib/api-client", () => ({
  refreshToken: (...args: unknown[]) => mockRefreshToken(...args),
  logout: (...args: unknown[]) => mockLogout(...args),
  getMfaSetup: (...args: unknown[]) => mockGetMfaSetup(...args),
  confirmMfaSetup: (...args: unknown[]) => mockConfirmMfaSetup(...args),
}));

// Auth store mock state
let mockAuthState = {
  accessToken: "test-token",
  user: {
    sub: "user-1",
    org: "org-1",
    roles: ["user"],
    displayName: "John Doe",
    orgName: "Test Organization",
    mfaEnabled: false,
  },
  isAuthenticated: true,
  isLoading: false,
  setTokens: vi.fn(),
  clearAuth: vi.fn(),
  refreshAuth: vi.fn(),
};

vi.mock("@/lib/auth-store", () => ({
  useAuthStore: (selector?: (s: typeof mockAuthState) => unknown) => {
    if (selector) return selector(mockAuthState);
    return mockAuthState;
  },
}));

// Import components after mocks
import { AppShell } from "./app-shell";
import { MfaGate } from "./mfa-gate";
import AuthenticatedLayout from "@/app/(authenticated)/layout";

describe("AppShell", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPathname.mockReturnValue("/");
    mockAuthState = {
      accessToken: "test-token",
      user: {
        sub: "user-1",
        org: "org-1",
        roles: ["user"],
        displayName: "John Doe",
        orgName: "Test Organization",
        mfaEnabled: false,
      },
      isAuthenticated: true,
      isLoading: false,
      setTokens: vi.fn(),
      clearAuth: vi.fn(),
      refreshAuth: vi.fn(),
    };
  });

  // AC-1: Navigation renders correctly with expected items
  it("AC-1: renders navigation with Dashboard, Needs, Products, Matches items", () => {
    render(
      <AppShell>
        <div>Content</div>
      </AppShell>
    );

    expect(screen.getByRole("navigation", { name: "Main navigation" })).toBeInTheDocument();
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Needs")).toBeInTheDocument();
    expect(screen.getByText("Products")).toBeInTheDocument();
    expect(screen.getByText("Matches")).toBeInTheDocument();
  });

  // AC-2: Admin nav item is hidden for non-admin users
  it("AC-2: hides Admin nav item for non-admin users", () => {
    mockAuthState.user.roles = ["user"];
    render(
      <AppShell>
        <div>Content</div>
      </AppShell>
    );

    expect(screen.queryByText("Admin")).not.toBeInTheDocument();
  });

  // AC-3: Admin nav item is shown for admin users
  it("AC-3: shows Admin nav item for admin users", () => {
    mockAuthState.user.roles = ["admin"];
    render(
      <AppShell>
        <div>Content</div>
      </AppShell>
    );

    expect(screen.getByText("Admin")).toBeInTheDocument();
  });

  // AC-4: Top bar shows user display name and org name (never raw UUID)
  it("AC-4: displays human-readable user name and organization name in top bar", () => {
    render(
      <AppShell>
        <div>Content</div>
      </AppShell>
    );

    expect(screen.getByText("John Doe")).toBeInTheDocument();
    expect(screen.getByText("Test Organization")).toBeInTheDocument();
    // Verify no raw UUIDs are shown
    expect(screen.queryByText("user-1")).not.toBeInTheDocument();
    expect(screen.queryByText("org-1")).not.toBeInTheDocument();
  });

  // AC-5: Logout button is present and functional
  it("AC-5: logout button calls logout and clears auth state", async () => {
    const user = userEvent.setup();
    mockLogout.mockResolvedValueOnce({ message: "ok" });

    render(
      <AppShell>
        <div>Content</div>
      </AppShell>
    );

    const logoutButton = screen.getByRole("button", { name: "Logout" });
    expect(logoutButton).toBeInTheDocument();

    await user.click(logoutButton);

    await waitFor(() => {
      expect(mockLogout).toHaveBeenCalled();
      expect(mockAuthState.clearAuth).toHaveBeenCalled();
    });
  });

  // AC-6: Sidebar collapses and shows tooltips
  it("AC-6: collapsed sidebar shows icons with tooltips", async () => {
    const user = userEvent.setup();

    render(
      <AppShell>
        <div>Content</div>
      </AppShell>
    );

    // Click collapse button
    const collapseButton = screen.getByLabelText("Collapse sidebar");
    await user.click(collapseButton);

    // Expand button should now be visible
    expect(screen.getByLabelText("Expand sidebar")).toBeInTheDocument();

    // Tooltips should exist (hidden by default, visible on hover via CSS)
    const tooltips = screen.getAllByRole("tooltip");
    expect(tooltips.length).toBeGreaterThan(0);
    expect(tooltips[0]).toHaveTextContent("Dashboard");
  });

  // AC-7: Active nav item uses primary-container background
  it("AC-7: active nav item has primary-container background", () => {
    mockPathname.mockReturnValue("/");

    render(
      <AppShell>
        <div>Content</div>
      </AppShell>
    );

    const dashboardLink = screen.getByText("Dashboard").closest("a");
    expect(dashboardLink).toHaveClass("bg-[#f2e1f4]");
    expect(dashboardLink).toHaveAttribute("aria-current", "page");
  });
});

describe("AuthenticatedLayout", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPathname.mockReturnValue("/");
    mockAuthState = {
      accessToken: "test-token",
      user: {
        sub: "user-1",
        org: "org-1",
        roles: ["user"],
        displayName: "John Doe",
        orgName: "Test Organization",
        mfaEnabled: false,
      },
      isAuthenticated: true,
      isLoading: false,
      setTokens: vi.fn(),
      clearAuth: vi.fn(),
      refreshAuth: vi.fn(),
    };
  });

  // AC-8: Unauthenticated users are redirected to /login
  it("AC-8: redirects to /login when not authenticated", async () => {
    mockAuthState.isAuthenticated = false;
    mockAuthState.isLoading = false;
    mockAuthState.user = null as unknown as typeof mockAuthState.user;

    render(
      <AuthenticatedLayout>
        <div>Protected Content</div>
      </AuthenticatedLayout>
    );

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/login");
    });
  });

  // AC-9: Shows loading state while checking auth
  it("AC-9: shows loading state while checking authentication", () => {
    mockAuthState.isLoading = true;
    mockAuthState.isAuthenticated = false;

    render(
      <AuthenticatedLayout>
        <div>Protected Content</div>
      </AuthenticatedLayout>
    );

    expect(screen.getByText("Loading...")).toBeInTheDocument();
    expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();
  });

  // AC-10: Renders children when authenticated
  it("AC-10: renders children when authenticated", () => {
    mockAuthState.isAuthenticated = true;
    mockAuthState.isLoading = false;

    render(
      <AuthenticatedLayout>
        <div>Protected Content</div>
      </AuthenticatedLayout>
    );

    expect(screen.getByText("Protected Content")).toBeInTheDocument();
  });
});

describe("MfaGate", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAuthState = {
      accessToken: "test-token",
      user: {
        sub: "user-1",
        org: "org-1",
        roles: ["admin"],
        displayName: "Admin User",
        orgName: "Test Organization",
        mfaEnabled: false,
      },
      isAuthenticated: true,
      isLoading: false,
      setTokens: vi.fn(),
      clearAuth: vi.fn(),
      refreshAuth: vi.fn(),
    };
  });

  // AC-11: MFA gate renders for admin without MFA
  it("AC-11: renders MFA setup gate with warning banner", async () => {
    mockGetMfaSetup.mockResolvedValueOnce({
      provisioningUri: "otpauth://totp/test?secret=ABCDEF",
      secret: "ABCDEF",
    });

    render(<MfaGate />);

    await waitFor(() => {
      expect(
        screen.getByText("Multi-factor authentication is required for your account")
      ).toBeInTheDocument();
    });

    expect(
      screen.getByText("Set Up Two-Factor Authentication")
    ).toBeInTheDocument();
  });

  // AC-12: MFA gate shows QR code and manual key
  it("AC-12: displays QR code and manual entry key after loading", async () => {
    mockGetMfaSetup.mockResolvedValueOnce({
      provisioningUri: "otpauth://totp/test?secret=ABCDEF123",
      secret: "ABCDEF123",
    });

    render(<MfaGate />);

    await waitFor(() => {
      expect(screen.getByRole("img")).toBeInTheDocument();
    });

    expect(screen.getByText("Manual entry key:")).toBeInTheDocument();
    expect(screen.getByText("ABCDEF123")).toBeInTheDocument();
  });

  // AC-13: MFA gate shows backup codes after verification
  it("AC-13: shows backup codes after successful verification", async () => {
    const user = userEvent.setup();
    mockGetMfaSetup.mockResolvedValueOnce({
      provisioningUri: "otpauth://totp/test?secret=ABCDEF",
      secret: "ABCDEF",
    });
    mockConfirmMfaSetup.mockResolvedValueOnce({
      backupCodes: ["code1", "code2", "code3", "code4"],
    });

    render(<MfaGate />);

    // Wait for setup to load
    await waitFor(() => {
      expect(screen.getByText("Continue")).toBeInTheDocument();
    });

    // Click continue to go to verify step
    await user.click(screen.getByText("Continue"));

    // Enter code
    const input = screen.getByLabelText("Verification Code");
    await user.type(input, "123456");

    // Submit
    await user.click(screen.getByRole("button", { name: "Verify" }));

    // Should show backup codes
    await waitFor(() => {
      expect(screen.getByText("code1")).toBeInTheDocument();
      expect(screen.getByText("code2")).toBeInTheDocument();
      expect(screen.getByText("code3")).toBeInTheDocument();
      expect(screen.getByText("code4")).toBeInTheDocument();
    });

    expect(
      screen.getByText("I have saved my backup codes")
    ).toBeInTheDocument();
  });

  // AC-14: MFA gate for admin in authenticated layout
  it("AC-14: authenticated layout shows MFA gate for admin without MFA", async () => {
    mockAuthState.user.roles = ["admin"];
    mockAuthState.user.mfaEnabled = false;
    mockPathname.mockReturnValue("/");
    mockGetMfaSetup.mockResolvedValueOnce({
      provisioningUri: "otpauth://totp/test?secret=XYZ",
      secret: "XYZ",
    });

    render(
      <AuthenticatedLayout>
        <div>Admin Dashboard</div>
      </AuthenticatedLayout>
    );

    await waitFor(() => {
      expect(
        screen.getByText("Multi-factor authentication is required for your account")
      ).toBeInTheDocument();
    });

    // Protected content should NOT be visible
    expect(screen.queryByText("Admin Dashboard")).not.toBeInTheDocument();
  });
});

describe("useSession", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAuthState = {
      accessToken: "test-token",
      user: {
        sub: "user-1",
        org: "org-1",
        roles: ["user"],
        displayName: "John Doe",
        orgName: "Test Organization",
        mfaEnabled: false,
      },
      isAuthenticated: true,
      isLoading: false,
      setTokens: vi.fn(),
      clearAuth: vi.fn(),
      refreshAuth: vi.fn(),
    };
  });

  // AC-15: Session hook attempts refresh on mount
  it("AC-15: attempts silent token refresh on mount", () => {
    render(
      <AuthenticatedLayout>
        <div>Content</div>
      </AuthenticatedLayout>
    );

    expect(mockAuthState.refreshAuth).toHaveBeenCalled();
  });
});
