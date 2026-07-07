"use client";

import { useState } from "react";
import { requestPasswordReset, ApiRequestError } from "@/lib/api-client";

export default function PasswordResetPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      await requestPasswordReset(email);
      setIsSuccess(true);
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

  if (isSuccess) {
    return (
      <div className="flex flex-col gap-lg">
        <h1 className="text-[22px] font-semibold leading-tight">Check Your Email</h1>
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
          <span className="text-[14px]">
            If an account exists with that email, you&apos;ll receive a password reset link.
          </span>
        </div>
        <a
          href="/login"
          className="text-center text-[12px] font-medium text-primary hover:underline focus:outline-none focus:ring-2 focus:ring-primary"
        >
          Back to Sign In
        </a>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-lg">
      <h1 className="text-[22px] font-semibold leading-tight">Reset Password</h1>
      <p className="text-[14px] text-gray-600">
        Enter your email address and we&apos;ll send you a link to reset your password.
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
          <label htmlFor="email" className="text-[14px] font-normal">
            Email
          </label>
          <input
            id="email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="rounded-md border border-gray-300 bg-surface px-md py-sm text-[14px] focus:outline-none focus:ring-2 focus:ring-primary"
            autoComplete="email"
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
            "Send Reset Link"
          )}
        </button>
      </form>

      <a
        href="/login"
        className="text-center text-[12px] font-medium text-primary hover:underline focus:outline-none focus:ring-2 focus:ring-primary"
      >
        Back to Sign In
      </a>
    </div>
  );
}
