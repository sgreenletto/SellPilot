export interface ApiResponse<T> {
  code: number | string;
  message: string;
  data: T;
  request_id: string;
}

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
