"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { verifyMfa, ApiRequestError } from "@/lib/api-client";
import { useAuthStore } from "@/lib/auth-store";

export default function MfaPage() {
  return (
    <Suspense fallback={<div className="flex justify-center p-lg"><span className="text-[14px] text-gray-600">Loading...</span></div>}>
      <MfaPageContent />
    </Suspense>
  );
}

function MfaPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const setTokens = useAuthStore((s) => s.setTokens);
  const mfaToken = searchParams.get("mfaToken") ?? "";

  const [code, setCode] = useState("");
  const [useBackupCode, setUseBackupCode] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const response = await verifyMfa({ mfaToken, code });
      setTokens(response);
      router.push("/");
    } catch (err) {
      if (err instanceof ApiRequestError) {
        setError(err.message);
      } else {
        setError("An unexpected error occurred. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-lg">
      <h1 className="text-[22px] font-semibold leading-tight">
        Two-Factor Authentication
      </h1>
      <p className="text-[14px] text-gray-600">
        {useBackupCode
          ? "Enter one of your backup codes."
          : "Enter the 6-digit code from your authenticator app."}
      </p>

      {error && (
        <div
          className="flex items-center gap-sm rounded-md bg-[#FEF2F2] p-md text-error"
          role="alert"
        >
          <svg
            aria-hidden="true"
            className="h-5 w-5 flex-shrink-0"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
              clipRule="evenodd"
            />
          </svg>
          <span className="text-[14px]">{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex flex-col gap-md">
        <div className="flex flex-col gap-xs">
          <label htmlFor="mfa-code" className="text-[14px] font-normal">
            {useBackupCode ? "Backup Code" : "Verification Code"}
          </label>
          <input
            id="mfa-code"
            type="text"
            required
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder={useBackupCode ? "" : "000000"}
            maxLength={useBackupCode ? 20 : 6}
            pattern={useBackupCode ? undefined : "[0-9]{6}"}
            inputMode={useBackupCode ? "text" : "numeric"}
            className="rounded-md border border-gray-300 bg-surface px-md py-sm text-[14px] focus:outline-none focus:ring-2 focus:ring-primary"
            autoComplete="one-time-code"
          />
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className="mt-sm flex items-center justify-center rounded-md bg-primary px-md py-sm text-[14px] font-medium text-white transition-opacity hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 disabled:opacity-50"
        >
          {isLoading ? (
            <svg
              className="h-5 w-5 animate-spin"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              aria-label="Loading"
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
          ) : (
            "Verify"
          )}
        </button>
      </form>

      <button
        type="button"
        onClick={() => {
          setUseBackupCode(!useBackupCode);
          setCode("");
          setError(null);
        }}
        className="text-center text-[12px] font-medium text-primary hover:underline focus:outline-none focus:ring-2 focus:ring-primary"
      >
        {useBackupCode ? "Use authenticator app" : "Use a backup code"}
      </button>
    </div>
  );
}
