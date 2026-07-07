"use client";

import { Suspense, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { z } from "zod";
import { confirmPasswordReset, ApiRequestError } from "@/lib/api-client";

const passwordSchema = z
  .string()
  .min(12, "Password must be at least 12 characters")
  .regex(/[A-Z]/, "Password must contain an uppercase letter")
  .regex(/[a-z]/, "Password must contain a lowercase letter")
  .regex(/[0-9]/, "Password must contain a digit")
  .regex(/[^A-Za-z0-9]/, "Password must contain a special character");

const resetSchema = z
  .object({
    password: passwordSchema,
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

export default function PasswordResetConfirmPage() {
  return (
    <Suspense fallback={<div className="flex justify-center p-lg"><span className="text-[14px] text-gray-600">Loading...</span></div>}>
      <PasswordResetConfirmPageContent />
    </Suspense>
  );
}

function PasswordResetConfirmPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setErrors({});
    setServerError(null);

    const result = resetSchema.safeParse({ password, confirmPassword });

    if (!result.success) {
      const fieldErrors: Record<string, string> = {};
      for (const issue of result.error.issues) {
        const field = issue.path[0];
        if (field && !fieldErrors[String(field)]) {
          fieldErrors[String(field)] = issue.message;
        }
      }
      setErrors(fieldErrors);
      return;
    }

    setIsLoading(true);

    try {
      await confirmPasswordReset({ token, password: result.data.password });
      router.push("/login");
    } catch (err) {
      if (err instanceof ApiRequestError) {
        setServerError(err.message);
      } else {
        setServerError("An unexpected error occurred. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  }

  if (!token) {
    return (
      <div className="flex flex-col gap-lg">
        <h1 className="text-[22px] font-semibold leading-tight">Invalid Link</h1>
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
          <span className="text-[14px]">No reset token provided. Please request a new password reset link.</span>
        </div>
        <a
          href="/password-reset"
          className="text-center text-[12px] font-medium text-primary hover:underline focus:outline-none focus:ring-2 focus:ring-primary"
        >
          Request New Link
        </a>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-lg">
      <h1 className="text-[22px] font-semibold leading-tight">Set New Password</h1>

      {serverError && (
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
          <span className="text-[14px]">{serverError}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex flex-col gap-md">
        <div className="flex flex-col gap-xs">
          <label htmlFor="password" className="text-[14px] font-normal">
            New Password
          </label>
          <input
            id="password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="rounded-md border border-gray-300 bg-surface px-md py-sm text-[14px] focus:outline-none focus:ring-2 focus:ring-primary"
            autoComplete="new-password"
          />
          {errors.password && (
            <span className="text-[12px] font-medium text-error">{errors.password}</span>
          )}
          <span className="text-[12px] font-medium text-gray-500">
            Min 12 characters, upper + lower + digit + symbol
          </span>
        </div>

        <div className="flex flex-col gap-xs">
          <label htmlFor="confirmPassword" className="text-[14px] font-normal">
            Confirm New Password
          </label>
          <input
            id="confirmPassword"
            type="password"
            required
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="rounded-md border border-gray-300 bg-surface px-md py-sm text-[14px] focus:outline-none focus:ring-2 focus:ring-primary"
            autoComplete="new-password"
          />
          {errors.confirmPassword && (
            <span className="text-[12px] font-medium text-error">{errors.confirmPassword}</span>
          )}
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
            "Reset Password"
          )}
        </button>
      </form>
    </div>
  );
}
