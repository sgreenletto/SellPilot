export type { ApiErrorResponse, ApiResponse, ValidationIssue } from "@/types/contracts";

export interface PlatformPingData {
  adapter: "mock" | "real";
  configured: boolean;
  reachable: boolean;
  message: string;
  capabilities: string[];
}

export interface FrontendApiErrorShape {
  code: string;
  message: string;
  status: number;
  requestId?: string;
  details?: unknown;
}
