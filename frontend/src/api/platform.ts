import { request } from "@/api/http";
import type { PlatformPingData } from "@/api/types";

export function getPlatformStatus(): Promise<PlatformPingData> {
  return request<PlatformPingData>("/v1/platform/status");
}
