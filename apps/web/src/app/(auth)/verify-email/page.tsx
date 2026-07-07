"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { verifyEmail, requestPasswordReset, ApiRequestError } from "@/lib/api-client";

type VerifyState = "loading" | "success" | "error";

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<div className="flex justify-center p-lg"><span className="text-[14px] text-gray-600">Loading...</span></div>}>
      <VerifyEmailPageContent />
    </Suspense>
  );
}

function VerifyEmailPageContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [state, setState] = useState<VerifyState>("loading");
  const [errorMessage, setErrorMessage] = useState("");
  const [resendEmail, setResendEmail] = useState("");
  const [resendSent, setResendSent] = useState(false);

  useEffect(() => {
    if (!token) {
      setState("error");
      setErrorMessage("No verification token provided.");
      return;
    }

    verifyEmail(token)
      .then(() => setState("success"))
      .catch((err) => {
        setState("error");
        if (err instanceof ApiRequestError) {
          setErrorMessage(err.message);
        } else {
          setErrorMessage("Verification failed. The token may be invalid or expired.");
        }
      });
  }, [token]);

  async function handleResend() {
    if (!resendEmail) return;
    try {
      await requestPasswordReset(resendEmail);
      setResendSent(true);
    } catch {
      // Silently handle - don't reveal if email exists
      setResendSent(true);
    }
  }

  if (state === "loading") {
    return (
      <div className="flex flex-col items-center gap-lg">
        <h1 className="text-[22px] font-semibold leading-tight">Verifying Email</h1>
        <svg
          className="h-8 w-8 animate-spin text-primary"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          aria-label="Verifying"
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
        <p className="text-[14px] text-gray-600">Please wait while we verify your email...</p>
      </div>
    );
  }

  if (state === "success") {
    return (
      <div className="flex flex-col gap-lg">
        <h1 className="text-[22px] font-semibold leading-tight">Email Verified</h1>
        <div className="flex items-center gap-sm rounded-md bg-[#ECFDF5] p-md text-success">
          <svg
            aria-hidden="true"
            className="h-5 w-5 flex-shrink-0"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
              clipRule="evenodd"
            />
          </svg>
          <span className="text-[14px]">Your email has been verified successfully.</span>
        </div>
        <a
          href="/login"
          className="text-center text-[14px] font-medium text-primary hover:underline focus:outline-none focus:ring-2 focus:ring-primary"
        >
          Continue to Sign In
        </a>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-lg">
      <h1 className="text-[22px] font-semibold leading-tight">Verification Failed</h1>
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
        <span className="text-[14px]">{errorMessage}</span>
      </div>

      {!resendSent ? (
        <div className="flex flex-col gap-sm">
          <p className="text-[12px] font-medium text-gray-600">
            Enter your email to receive a new verification link.
          </p>
          <div className="flex gap-sm">
            <input
              type="email"
              value={resendEmail}
              onChange={(e) => setResendEmail(e.target.value)}
              placeholder="your@email.com"
              className="flex-1 rounded-md border border-gray-300 bg-surface px-md py-sm text-[14px] focus:outline-none focus:ring-2 focus:ring-primary"
              aria-label="Email for resend"
            />
            <button
              type="button"
              onClick={handleResend}
              className="rounded-md bg-primary px-md py-sm text-[14px] font-medium text-white hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
            >
              Resend
            </button>
          </div>
        </div>
      ) : (
        <p className="text-[14px] text-gray-600">
          If an account exists with that email, a new verification link has been sent.
        </p>
      )}
    </div>
  );
}
