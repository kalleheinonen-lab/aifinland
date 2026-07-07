const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;

if (!API_BASE_URL) {
  throw new Error(
    "NEXT_PUBLIC_API_URL environment variable is not set. " +
      "Please set it to the API base URL (e.g., https://api.example.com)."
  );
}

export interface ApiError {
  code: string;
  message: string;
}

export class ApiRequestError extends Error {
  public readonly code: string;
  public readonly status: number;

  constructor(message: string, code: string, status: number) {
    super(message);
    this.name = "ApiRequestError";
    this.code = code;
    this.status = status;
  }
}

interface ApiResponse<T> {
  data: T | null;
  meta: { requestId?: string; timestamp?: string };
  error: ApiError | null;
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${path}`;

  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  const body = (await response.json()) as ApiResponse<T>;

  if (!response.ok || body.error) {
    const error = body.error ?? { code: "UNKNOWN_ERROR", message: "An unexpected error occurred" };
    throw new ApiRequestError(error.message, error.code, response.status);
  }

  return body.data as T;
}

export interface RegisterInput {
  email: string;
  displayName: string;
  password: string;
}

export interface LoginInput {
  email: string;
  password: string;
}

export interface LoginResponse {
  accessToken: string;
  user: {
    sub: string;
    org: string;
    roles: string[];
    displayName: string;
    orgName: string;
    mfaEnabled: boolean;
  };
  mfaRequired?: boolean;
  mfaToken?: string;
}

export interface MfaSetupResponse {
  provisioningUri: string;
  secret: string;
}

export interface MfaSetupConfirmResponse {
  backupCodes: string[];
}

export function getMfaSetup(accessToken: string): Promise<MfaSetupResponse> {
  return request("/v1/auth/mfa/setup", {
    method: "GET",
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}

export function confirmMfaSetup(
  accessToken: string,
  code: string
): Promise<MfaSetupConfirmResponse> {
  return request("/v1/auth/mfa/setup/confirm", {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({ code }),
  });
}

export interface MfaVerifyInput {
  mfaToken: string;
  code: string;
}

export interface PasswordResetConfirmInput {
  token: string;
  password: string;
}

export function register(input: RegisterInput): Promise<{ message: string }> {
  return request("/v1/auth/register", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function login(input: LoginInput): Promise<LoginResponse> {
  return request("/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function verifyEmail(token: string): Promise<{ message: string }> {
  return request("/v1/auth/verify-email", {
    method: "POST",
    body: JSON.stringify({ token }),
  });
}

export function verifyMfa(input: MfaVerifyInput): Promise<LoginResponse> {
  return request("/v1/auth/mfa/verify", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function refreshToken(): Promise<LoginResponse> {
  return request("/v1/auth/refresh", {
    method: "POST",
    credentials: "include",
  });
}

export function logout(): Promise<{ message: string }> {
  return request("/v1/auth/logout", {
    method: "POST",
    credentials: "include",
  });
}

export function requestPasswordReset(email: string): Promise<{ message: string }> {
  return request("/v1/auth/password-reset/request", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export function confirmPasswordReset(input: PasswordResetConfirmInput): Promise<{ message: string }> {
  return request("/v1/auth/password-reset/confirm", {
    method: "POST",
    body: JSON.stringify(input),
  });
}
