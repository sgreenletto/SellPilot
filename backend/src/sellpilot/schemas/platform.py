from pydantic import BaseModel


class PlatformPingResult(BaseModel):
    adapter: str
    configured: bool
    reachable: bool
    message: str


class PlatformStatusResponse(BaseModel):
    adapter: str
    configured: bool
    reachable: bool
    message: str
    capabilities: list[str]
