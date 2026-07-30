[CmdletBinding()]
param(
    [string]$ApiBaseUrl,
    [switch]$RequireKnowledge
)

$ErrorActionPreference = "Stop"
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$backendRoot = Join-Path $repositoryRoot "backend"

function Invoke-SellPilotEndpoint {
    param([Parameter(Mandatory)][string]$Uri)

    $response = Invoke-RestMethod -Uri $Uri -TimeoutSec 10
    if ($response.code -ne 0) {
        throw "SellPilot endpoint returned code '$($response.code)' for $Uri"
    }
    return $response.data
}

if (-not $ApiBaseUrl) {
    Push-Location $backendRoot
    try {
        $proxyTarget = (& uv run sellpilot-start-api --print-proxy-target).Trim()
        if ($LASTEXITCODE -ne 0 -or -not $proxyTarget) {
            throw "无法读取 SellPilot API 地址。"
        }
    }
    finally {
        Pop-Location
    }
    $ApiBaseUrl = "$($proxyTarget.TrimEnd('/'))/api"
}

$live = Invoke-SellPilotEndpoint -Uri "$ApiBaseUrl/v1/health/live"
$ready = Invoke-SellPilotEndpoint -Uri "$ApiBaseUrl/v1/health/ready"

Push-Location $backendRoot
try {
    $snapshotJson = & uv run sellpilot-check-demo-readiness
    if ($LASTEXITCODE -ne 0) {
        throw "数据库就绪检查命令执行失败。"
    }
    $snapshot = $snapshotJson | ConvertFrom-Json
}
finally {
    Pop-Location
}

Write-Host "SellPilot Demo Readiness"
Write-Host "  live: $($live.status)"
Write-Host "  ready: $($ready.status), database=$($ready.database)"
Write-Host "  alembic: $($snapshot.database.alembic_version)"
Write-Host "  adapter: $($snapshot.configuration.platform_adapter)"
Write-Host "  content provider: $($snapshot.configuration.content_model_provider)"
Write-Host "  external LLM configured: $($snapshot.configuration.llm_configured)"
Write-Host "  data:"
$snapshot.data.PSObject.Properties | ForEach-Object {
    Write-Host "    $($_.Name): $($_.Value)"
}
Write-Host "  knowledge:"
Write-Host "    status: $($snapshot.knowledge.status)"
Write-Host "    indexed documents: $($snapshot.knowledge.indexed_documents)"
Write-Host "    indexed chunks: $($snapshot.knowledge.indexed_chunks)"
Write-Host "    embedded chunks: $($snapshot.knowledge.embedded_chunks)"
Write-Host "    real documents: $($snapshot.knowledge.real_documents)"
Write-Host "    real chunks: $($snapshot.knowledge.real_chunks)"
Write-Host "    Mock documents: $($snapshot.knowledge.mock_documents)"
Write-Host "    Mock chunks: $($snapshot.knowledge.mock_chunks)"
Write-Host "  overall: $($snapshot.overall_status)"

if ($snapshot.overall_status -eq "NOT_READY") {
    exit 1
}
if ($RequireKnowledge -and $snapshot.knowledge.status -ne "READY") {
    Write-Error "知识库尚未完成初始化：BLOCKED_RAG_DATA"
    exit 2
}
if ($snapshot.knowledge.status -ne "READY") {
    Write-Warning "BLOCKED_RAG_DATA：核心 Demo 可用，但仍需导入并验证真实知识数据。"
}

exit 0
