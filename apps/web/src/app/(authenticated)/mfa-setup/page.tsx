"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { QRCodeSVG } from "qrcode.react";
import { useAuthStore } from "@/lib/auth-store";
import { getMfaSetup, confirmMfaSetup, ApiRequestError } from "@/lib/api-client";

type SetupStep = "intro" | "qrcode" | "verify" | "backup_codes";

function StepIndicator({
  current,
  total,
  label,
}: {
  current: number;
  total: number;
  label: string;
}) {
  return (
    <div className="mb-lg flex items-center gap-sm">
      <span
        className="flex h-6 w-6 items-center justify-center rounded-full text-[12px] font-semibold text-primary"
        style={{ backgroundColor: "#f2e1f4" }}
        aria-label={`Step ${current} of ${total}`}
      >
        {current}
      </span>
      <span className="text-[13px] font-medium text-[#49454f]">
        {label}
      </span>
      <span className="ml-auto text-[12px] text-[#49454f] opacity-60">
        {current} / {total}
      </span>
    </div>
  );
}

function SkeletonQR() {
  return (
    <div
      className="mb-md flex justify-center"
      role="status"
      aria-label="Loading QR code"
    >
      <div
        className="h-[200px] w-[200px] animate-pulse rounded-md"
        style={{ backgroundColor: "rgba(0,0,0,0.08)" }}
      />
    </div>
  );
}

export default function MfaSetupPage() {
  const router = useRouter();
  const accessToken = useAuthStore((s) => s.accessToken);
  const refreshAuth = useAuthStore((s) => s.refreshAuth);

  const [step, setStep] = useState<SetupStep>("intro");
  const [provisioningUri, setProvisioningUri] = useState("");
  const [secret, setSecret] = useState("");
  const [code, setCode] = useState("");
  const [backupCodes, setBackupCodes] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [isLoadingSetup, setIsLoadingSetup] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [savedCodes, setSavedCodes] = useState(false);
  const [copied, setCopied] = useState(false);

  const loadSetup = useCallback(async () => {
    if (!accessToken) return;
    setIsLoadingSetup(true);
    setError("");
    try {
      const data = await getMfaSetup(accessToken);
      setProvisioningUri(data.provisioningUri);
      setSecret(data.secret);
    } catch {
      setError("Failed to load MFA setup. Please try again.");
    } finally {
      setIsLoadingSetup(false);
    }
  }, [accessToken]);

  const handleContinueToQR = useCallback(async () => {
    setStep("qrcode");
    await loadSetup();
  }, [loadSetup]);

  const handleVerify = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!accessToken || code.length !== 6) return;

      setIsSubmitting(true);
      setError("");

      try {
        const result = await confirmMfaSetup(accessToken, code);
        setBackupCodes(result.backupCodes);
        setStep("backup_codes");
      } catch (err) {
        if (err instanceof ApiRequestError && err.status === 401) {
          setError("Invalid code. Please try again.");
        } else {
          setError("Something went wrong. Please try again.");
        }
      } finally {
        setIsSubmitting(false);
      }
    },
    [accessToken, code]
  );

  const handleCopyAll = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(backupCodes.join("\n"));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API not available — silently ignore
    }
  }, [backupCodes]);

  const handleComplete = useCallback(async () => {
    await refreshAuth();
    router.push("/");
  }, [refreshAuth, router]);

  const STEP_LABELS: Record<SetupStep, string> = {
    intro: "Introduction",
    qrcode: "Scan QR Code",
    verify: "Verify Code",
    backup_codes: "Save Backup Codes",
  };

  const STEP_NUMBERS: Record<SetupStep, number> = {
    intro: 1,
    qrcode: 2,
    verify: 3,
    backup_codes: 4,
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface p-md">
      <div
        className="w-full max-w-[520px] rounded-lg p-lg shadow-md"
        style={{ backgroundColor: "#fdfcfd" }}
      >
        {/* Step indicator */}
        <StepIndicator
          current={STEP_NUMBERS[step]}
          total={4}
          label={STEP_LABELS[step]}
        />

        {/* ── Step 1: Introduction ── */}
        {step === "intro" && (
          <div>
            <h1
              className="mb-md font-semibold text-[#2c1f2e]"
              style={{ fontSize: "18px" }}
            >
              Set Up Two-Factor Authentication
            </h1>

            <p
              className="mb-md text-[#49454f]"
              style={{ fontSize: "14px", fontWeight: 400 }}
            >
              Your account has an Admin or Super Admin role. To protect the
              platform and its users, multi-factor authentication (MFA) is
              mandatory for all privileged accounts.
            </p>

            <p
              className="mb-lg text-[#49454f]"
              style={{ fontSize: "14px", fontWeight: 400 }}
            >
              You will need an authenticator app such as{" "}
              <strong>Google Authenticator</strong>,{" "}
              <strong>Authy</strong>, or{" "}
              <strong>1Password</strong> installed on your phone or computer.
            </p>

            <ul
              className="mb-lg list-none space-y-sm"
              aria-label="Setup steps overview"
            >
              {[
                "Scan a QR code with your authenticator app",
                "Enter a 6-digit code to confirm setup",
                "Save 10 backup codes in a secure location",
              ].map((item, i) => (
                <li key={i} className="flex items-start gap-sm">
                  <span
                    className="mt-[2px] flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold text-primary"
                    style={{ backgroundColor: "#f2e1f4" }}
                    aria-hidden="true"
                  >
                    {i + 1}
                  </span>
                  <span
                    className="text-[#49454f]"
                    style={{ fontSize: "14px", fontWeight: 400 }}
                  >
                    {item}
                  </span>
                </li>
              ))}
            </ul>

            <button
              onClick={handleContinueToQR}
              className="w-full rounded-md bg-primary px-md py-sm text-[14px] font-medium text-white hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-primary"
            >
              Get Started
            </button>
          </div>
        )}

        {/* ── Step 2: QR Code ── */}
        {step === "qrcode" && (
          <div>
            <h1
              className="mb-md font-semibold text-[#2c1f2e]"
              style={{ fontSize: "18px" }}
            >
              Scan the QR Code
            </h1>

            <p
              className="mb-md text-[#49454f]"
              style={{ fontSize: "14px", fontWeight: 400 }}
            >
              Open your authenticator app and scan the QR code below. If you
              cannot scan, use the manual entry key instead.
            </p>

            {error && (
              <div
                className="mb-md rounded-md px-md py-sm"
                style={{ backgroundColor: "#fef2f2" }}
                role="alert"
              >
                <span
                  className="text-[14px]"
                  style={{ color: "#DC2626" }}
                >
                  {error}
                </span>
                <button
                  onClick={loadSetup}
                  className="ml-sm text-[14px] font-medium underline"
                  style={{ color: "#DC2626" }}
                >
                  Retry
                </button>
              </div>
            )}

            {isLoadingSetup ? (
              <SkeletonQR />
            ) : (
              provisioningUri && (
                <div className="mb-md flex justify-center">
                  <QRCodeSVG
                    value={provisioningUri}
                    size={200}
                    className="rounded-md border"
                    style={{ borderColor: "rgba(0,0,0,0.08)" }}
                  />
                </div>
              )
            )}

            {!isLoadingSetup && secret && (
              <div
                className="mb-lg rounded-md border p-sm"
                style={{
                  borderColor: "rgba(0,0,0,0.08)",
                  backgroundColor: "#f7f5f7",
                }}
              >
                <p className="mb-xs text-[12px] font-medium text-[#49454f]">
                  Manual entry key:
                </p>
                <code
                  className="select-all font-mono text-[#2c1f2e]"
                  style={{ fontSize: "14px" }}
                >
                  {secret}
                </code>
              </div>
            )}

            <button
              onClick={() => setStep("verify")}
              disabled={isLoadingSetup || (!provisioningUri && !error)}
              className="w-full rounded-md bg-primary px-md py-sm text-[14px] font-medium text-white hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
            >
              Continue
            </button>
          </div>
        )}

        {/* ── Step 3: Verify ── */}
        {step === "verify" && (
          <div>
            <h1
              className="mb-md font-semibold text-[#2c1f2e]"
              style={{ fontSize: "18px" }}
            >
              Enter Verification Code
            </h1>

            <p
              className="mb-md text-[#49454f]"
              style={{ fontSize: "14px", fontWeight: 400 }}
            >
              Enter the 6-digit code shown in your authenticator app to confirm
              setup.
            </p>

            {error && (
              <div
                className="mb-md rounded-md px-md py-sm"
                style={{ backgroundColor: "#fef2f2" }}
                role="alert"
              >
                <span
                  className="text-[14px]"
                  style={{ color: "#DC2626" }}
                >
                  {error}
                </span>
              </div>
            )}

            <form onSubmit={handleVerify}>
              <div className="mb-md">
                <label
                  htmlFor="mfa-code"
                  className="mb-xs block text-[12px] font-medium text-[#49454f]"
                >
                  Verification Code
                </label>
                <input
                  id="mfa-code"
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]{6}"
                  maxLength={6}
                  value={code}
                  onChange={(e) =>
                    setCode(e.target.value.replace(/\D/g, ""))
                  }
                  placeholder="000000"
                  className="w-full rounded-md border px-md py-sm text-center text-[18px] font-mono tracking-[0.5em] focus:outline-none focus:ring-2 focus:ring-primary"
                  style={{ borderColor: "rgba(0,0,0,0.08)" }}
                  autoComplete="one-time-code"
                  required
                />
              </div>

              <button
                type="submit"
                disabled={code.length !== 6 || isSubmitting}
                className="w-full rounded-md bg-primary px-md py-sm text-[14px] font-medium text-white hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
              >
                {isSubmitting ? (
                  <span className="flex items-center justify-center gap-sm">
                    <svg
                      className="h-4 w-4 animate-spin"
                      viewBox="0 0 24 24"
                      fill="none"
                      aria-hidden="true"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                      />
                    </svg>
                    Verifying...
                  </span>
                ) : (
                  "Verify"
                )}
              </button>
            </form>
          </div>
        )}

        {/* ── Step 4: Backup Codes ── */}
        {step === "backup_codes" && (
          <div>
            <h1
              className="mb-md font-semibold text-[#2c1f2e]"
              style={{ fontSize: "18px" }}
            >
              Save Your Backup Codes
            </h1>

            {/* Warning banner */}
            <div
              className="mb-md flex items-start gap-sm rounded-md px-md py-sm"
              style={{ backgroundColor: "#FFFBEB" }}
              role="alert"
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 20 20"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
                aria-hidden="true"
                className="mt-[1px] shrink-0"
              >
                <path
                  d="M10 3L2 17H18L10 3Z"
                  stroke="#D97706"
                  strokeWidth="1.5"
                  strokeLinejoin="round"
                />
                <path
                  d="M10 8V11M10 14V14.01"
                  stroke="#D97706"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                />
              </svg>
              <span
                className="text-[14px] font-medium"
                style={{ color: "#D97706" }}
              >
                Save these codes securely. They cannot be shown again.
              </span>
            </div>

            {/* Backup codes grid */}
            <div
              className="mb-md rounded-md border p-md"
              style={{
                borderColor: "rgba(0,0,0,0.08)",
                backgroundColor: "#f7f5f7",
              }}
            >
              <div className="grid grid-cols-2 gap-sm">
                {backupCodes.map((backupCode, index) => (
                  <code
                    key={index}
                    className="font-mono text-[#2c1f2e]"
                    style={{ fontSize: "13px", fontWeight: 400 }}
                  >
                    {backupCode}
                  </code>
                ))}
              </div>
            </div>

            {/* Copy-all button */}
            <button
              onClick={handleCopyAll}
              className="mb-md flex w-full items-center justify-center gap-sm rounded-md border px-md py-sm text-[14px] font-medium text-[#2c1f2e] hover:bg-[#f7f5f7] focus:outline-none focus:ring-2 focus:ring-primary"
              style={{ borderColor: "rgba(0,0,0,0.08)" }}
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
                aria-hidden="true"
              >
                <rect
                  x="5"
                  y="5"
                  width="9"
                  height="9"
                  rx="1.5"
                  stroke="currentColor"
                  strokeWidth="1.5"
                />
                <path
                  d="M11 5V3.5A1.5 1.5 0 009.5 2h-6A1.5 1.5 0 002 3.5v6A1.5 1.5 0 003.5 11H5"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                />
              </svg>
              {copied ? "Copied!" : "Copy all codes"}
            </button>

            {/* Confirmation checkbox */}
            <label className="mb-lg flex cursor-pointer items-start gap-sm">
              <input
                type="checkbox"
                checked={savedCodes}
                onChange={(e) => setSavedCodes(e.target.checked)}
                className="mt-[2px] h-4 w-4 rounded accent-primary"
              />
              <span
                className="text-[#49454f]"
                style={{ fontSize: "14px", fontWeight: 400 }}
              >
                I have saved my backup codes
              </span>
            </label>

            <button
              onClick={handleComplete}
              disabled={!savedCodes}
              className="w-full rounded-md bg-primary px-md py-sm text-[14px] font-medium text-white hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
            >
              Continue to Dashboard
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
