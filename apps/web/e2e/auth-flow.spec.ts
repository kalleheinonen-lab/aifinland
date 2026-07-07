import { test, expect } from "@playwright/test";

/**
 * AC-11 [e2e]: Full browser authentication lifecycle.
 *
 * WHEN a Playwright test registers a user, retrieves the verification token,
 * verifies email, logs in via the login page, sees the authenticated app shell,
 * and clicks logout, THE SYSTEM SHALL complete the full browser flow against
 * the real API and real Valkey.
 *
 * kills: missing CORS headers block cross-origin requests, broken form submission,
 *        auth state not persisted after login, logout not clearing session
 */
test.describe("AC-11: full browser auth lifecycle", () => {
  const TEST_EMAIL = `e2e-${Date.now()}@test.example.com`;
  const TEST_DISPLAY_NAME = "E2E Test User";
  const TEST_PASSWORD = "SecureP@ss1234!";

  test("register, verify email, login, see dashboard, logout", async ({
    page,
    request,
  }) => {
    // Step 1: Navigate to /register and fill in the form
    await page.goto("/register");
    await expect(page.getByRole("heading", { name: "Create Account" })).toBeVisible();

    await page.getByLabel("Email").fill(TEST_EMAIL);
    await page.getByLabel("Display Name").fill(TEST_DISPLAY_NAME);
    await page.getByLabel("Password", { exact: true }).fill(TEST_PASSWORD);
    await page.getByLabel("Confirm Password").fill(TEST_PASSWORD);

    // Submit the registration form
    await page.getByRole("button", { name: "Create Account" }).click();

    // Step 2: Assert success state - 'Check Your Email' message visible
    await expect(
      page.getByRole("heading", { name: "Check Your Email" })
    ).toBeVisible({ timeout: 15_000 });
    await expect(
      page.getByText("We've sent a verification link to your email")
    ).toBeVisible();

    // Step 3: Retrieve the email verification token via test-only endpoint
    const tokenResponse = await request.get(
      `http://localhost:8000/v1/auth/_test/verification-token?email=${encodeURIComponent(TEST_EMAIL)}`
    );
    expect(tokenResponse.ok()).toBeTruthy();
    const { token } = await tokenResponse.json();
    expect(token).toBeTruthy();

    // Step 4: Navigate to /verify-email with the token, assert success
    await page.goto(`/verify-email?token=${token}`);
    await expect(
      page.getByRole("heading", { name: "Email Verified" })
    ).toBeVisible({ timeout: 15_000 });
    await expect(
      page.getByText("Your email has been verified successfully")
    ).toBeVisible();

    // Step 5: Navigate to /login, fill in credentials, submit
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: "Sign In" })).toBeVisible();

    await page.getByLabel("Email").fill(TEST_EMAIL);
    await page.getByLabel("Password").fill(TEST_PASSWORD);
    await page.getByRole("button", { name: "Sign In" }).click();

    // Step 6: Assert redirect to authenticated app shell (dashboard)
    await expect(
      page.getByText("Welcome to AI Finland Platform")
    ).toBeVisible({ timeout: 15_000 });

    // Step 7: Click the logout button
    await page.getByRole("button", { name: "Logout" }).click();

    // Step 8: Assert redirect back to /login page
    await expect(page.getByRole("heading", { name: "Sign In" })).toBeVisible({
      timeout: 15_000,
    });
    await expect(page).toHaveURL(/\/login/);
  });
});
