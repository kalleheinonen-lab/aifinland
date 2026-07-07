"use client";

import { useState, useCallback, useEffect } from "react";
import { QRCodeSVG } from "qrcode.react";
import { useAuthStore } from "@/lib/auth-store";
import { getMfaSetup, confirmMfaSetup } from "@/lib/api-client";

type MfaStep = "loading" | "setup" | "verify" | "backup_codes";

export function MfaGate() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const refreshAuth = useAuthStore((s) => s.refreshAuth);
  const [step, setStep] = useState<MfaStep>("loading");
  const [provisioningUri, setProvisioningUri] = useState("");
  const [secret, setSecret] = useState("");
  const [code, setCode] = useState("");
  const [backupCodes, setBackupCodes] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadSetup = useCallback(async () => {
    if (!accessToken) return;
    try {
      const data = await getMfaSetup(accessToken);
      setProvisioningUri(data.provisioningUri);
      setSecret(data.secret);
      setStep("setup");
    } catch {
      setError("Failed to load MFA setup. Please try again.");
      setStep("setup");
    }
  }, [accessToken]);

  // Load setup on first render
  useEffect(() => {
    loadSetup();
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
      } catch {
        setError("Invalid code. Please try again.");
      } finally {
        setIsSubmitting(false);
      }
    },
    [accessToken, code]
  );

  const handleComplete = useCallback(async () => {
    await refreshAuth();
  }, [refreshAuth]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface p-md">
      <div className="w-full max-w-[480px] rounded-lg bg-white p-lg shadow-md">
        {/* Warning banner */}
        <div
          className="mb-lg rounded-md px-md py-sm"
          style={{ backgroundColor: "#FFFBEB" }}
          role="alert"
        >
          <div className="flex items-center gap-sm">
            <svg
              width="20"
              height="20"
              viewBox="0 0 20 20"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
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
            <span className="text-[14px] font-medium" style={{ color: "#D97706" }}>
              Multi-factor authentication is required for your account
            </span>
          </div>
        </div>

        <h1 className="mb-md text-[22px] font-semibold text-[#2c1f2e]">
          Set Up Two-Factor Authentication
        </h1>

        {step === "loading" && (
          <div className="flex items-center justify-center py-xl">
            <span className="text-[14px] text-[#49454f]">Loading MFA setup...</span>
          </div>
        )}

        {step === "setup" && (
          <div>
            <p className="mb-md text-[14px] text-[#49454f]">
              Scan the QR code below with your authenticator app, or enter the
              secret key manually.
            </p>

            {provisioningUri && (
              <div className="mb-md flex justify-center">
                {/* QR code rendered client-side — secret never sent to any external service */}
                <QRCodeSVG
                  value={provisioningUri}
                  size={200}
                  className="rounded-md border border-[rgba(0,0,0,0.08)]"
                />
              </div>
            )}

            {secret && (
              <div className="mb-md rounded-md border border-[rgba(0,0,0,0.08)] bg-[#f7f5f7] p-sm">
                <p className="mb-xs text-[12px] font-medium text-[#49454f]">
                  Manual entry key:
                </p>
                <code className="select-all text-[14px] font-mono text-[#2c1f2e]">
                  {secret}
                </code>
              </div>
            )}

            <button
              onClick={() => setStep("verify")}
              className="w-full rounded-md bg-primary px-md py-sm text-[14px] font-medium text-white hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-primary"
            >
              Continue
            </button>
          </div>
        )}

        {step === "verify" && (
          <form onSubmit={handleVerify}>
            <p className="mb-md text-[14px] text-[#49454f]">
              Enter the 6-digit code from your authenticator app to verify setup.
            </p>

            {error && (
              <div className="mb-md rounded-md bg-red-50 px-md py-sm" role="alert">
                <span className="text-[14px] text-error">{error}</span>
              </div>
            )}

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
                onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                placeholder="000000"
                className="w-full rounded-md border border-[rgba(0,0,0,0.08)] px-md py-sm text-center text-[18px] font-mono tracking-[0.5em] focus:outline-none focus:ring-2 focus:ring-primary"
                autoComplete="one-time-code"
                required
              />
            </div>

            <button
              type="submit"
              disabled={code.length !== 6 || isSubmitting}
              className="w-full rounded-md bg-primary px-md py-sm text-[14px] font-medium text-white hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
            >
              {isSubmitting ? "Verifying..." : "Verify"}
            </button>
          </form>
        )}

        {step === "backup_codes" && (
          <div>
            <p className="mb-md text-[14px] text-[#49454f]">
              Save these backup codes in a secure location. Each code can only be
              used once.
            </p>

            <div className="mb-md rounded-md border border-[rgba(0,0,0,0.08)] bg-[#f7f5f7] p-md">
              <div className="grid grid-cols-2 gap-sm">
                {backupCodes.map((backupCode, index) => (
                  <code
                    key={index}
                    className="text-[14px] font-mono text-[#2c1f2e]"
                  >
                    {backupCode}
                  </code>
                ))}
              </div>
            </div>

            <button
              onClick={handleComplete}
              className="w-full rounded-md bg-primary px-md py-sm text-[14px] font-medium text-white hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-primary"
            >
              I have saved my backup codes
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
