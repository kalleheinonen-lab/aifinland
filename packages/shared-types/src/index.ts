/**
 * Shared types for the AI Finland Matchmaking Platform.
 *
 * This package provides TypeScript type definitions shared between
 * the frontend (apps/web) and API client code.
 */

export interface HealthResponse {
  status: "ok";
}

export interface ApiErrorResponse {
  error: string;
  code: string;
}

export interface ApiResponse<T> {
  data: T;
  meta?: {
    requestId: string;
    timestamp: string;
  };
}
