"use client";

import { useState } from "react";
import { z } from "zod";
import Link from "next/link";
import { register, ApiRequestError } from "@/lib/api-client";

const passwordSchema = z
  .string()
  .min(12, "Password must be at least 12 characters")
  .regex(/[A-Z]/, "Password must contain an uppercase letter")
  .regex(/[a-z]/, "Password must contain a lowercase letter")
  .regex(/[0-9]/, "Password must contain a digit")
  .regex(/[^A-Za-z0-9]/, "Password must contain a special character");

const registerSchema = z
  .object({
    email: z.string().email("Please enter a valid email address"),
    displayName: z.string().min(1, "Display name is required"),
    password: passwordSchema,
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setErrors({});
    setServerError(null);

    const result = registerSchema.safeParse({
      email,
      displayName,
      password,
      confirmPassword,
    });

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
      await register({
        email: result.data.email,
        displayName: result.data.displayName,
        password: result.data.password,
      });
      setIsSuccess(true);
    } catch (err) {
      if (err instanceof ApiRequestError) {
        if (err.status === 409) {
          setServerError("An account with this email already exists.");
        } else {
          setServerError(err.message);
        }
      } else {
        setServerError("An unexpected error occurred. Please try again.");
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
            We&apos;ve sent a verification link to your email. Please check your inbox.
          </span>
        </div>
        <Link
          href="/login"
          className="text-center text-[12px] font-medium text-primary hover:underline focus:outline-none focus:ring-2 focus:ring-primary"
        >
          Back to Sign In
        </Link>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-lg">
      <h1 className="text-[22px] font-semibold leading-tight">Create Account</h1>

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
          {errors.email && (
            <span className="text-[12px] font-medium text-error">{errors.email}</span>
          )}
        </div>

        <div className="flex flex-col gap-xs">
          <label htmlFor="displayName" className="text-[14px] font-normal">
            Display Name
          </label>
          <input
            id="displayName"
            type="text"
            required
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            className="rounded-md border border-gray-300 bg-surface px-md py-sm text-[14px] focus:outline-none focus:ring-2 focus:ring-primary"
            autoComplete="name"
          />
          {errors.displayName && (
            <span className="text-[12px] font-medium text-error">{errors.displayName}</span>
          )}
        </div>

        <div className="flex flex-col gap-xs">
          <label htmlFor="password" className="text-[14px] font-normal">
            Password
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
            Confirm Password
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
            "Create Account"
          )}
        </button>
      </form>

      <Link
        href="/login"
        className="text-center text-[12px] font-medium text-primary hover:underline focus:outline-none focus:ring-2 focus:ring-primary"
      >
        Already have an account? Sign In
      </Link>
    </div>
  );
}
