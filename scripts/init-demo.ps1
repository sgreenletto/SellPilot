[CmdletBinding()]
param(
    [string]$AdminUsername,
    [switch]$IncludeKnowledge
)

$ErrorActionPreference = "Stop"
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$backendRoot = Join-Path $repositoryRoot "backend"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "未找到 uv，请先安装 uv 并加入 PATH。"
}
if (-not (Test-Path (Join-Path $repositoryRoot ".env"))) {
    throw "根目录 .env 不存在。请从 .env.example 创建本地配置，且不要提交 .env。"
}
if (Test-Path (Join-Path $backendRoot ".env")) {
    throw "检测到 backend/.env。SellPilot 只允许根目录 .env，请先人工核对并移除错误配置。"
}

Push-Location $backendRoot
try {
    Write-Host "[1/5] 检查并升级 PostgreSQL 迁移..."
    & uv run alembic upgrade head
    if ($LASTEXITCODE -ne 0) {
        throw "Alembic upgrade 失败。"
    }

    Write-Host "[2/5] 检查管理员状态..."
    $beforeJson = & uv run sellpilot-check-demo-readiness
    if ($LASTEXITCODE -ne 0) {
        throw "数据库状态检查失败。"
    }
    $before = $beforeJson | ConvertFrom-Json
    if ([int]$before.data.administrators -eq 0) {
        if (-not $AdminUsername) {
            throw "尚无管理员。请使用 -AdminUsername 指定用户名，密码将在隐藏提示中输入。"
        }
        & uv run sellpilot-create-admin --username $AdminUsername
        if ($LASTEXITCODE -ne 0) {
            throw "管理员创建失败。"
        }
    }
    else {
        Write-Host "  已存在管理员，跳过创建。"
    }

    Write-Host "[3/5] 幂等导入 Mock 商业数据..."
    & uv run sellpilot-import-mock-data
    if ($LASTEXITCODE -ne 0) {
        throw "Mock 数据导入失败。"
    }

    Write-Host "[4/5] 处理知识数据..."
    if ($IncludeKnowledge) {
        & uv run sellpilot-import-knowledge
        if ($LASTEXITCODE -ne 0) {
            throw "知识数据导入失败；已有 PostgreSQL 数据未被清空。"
        }
    }
    else {
        Write-Host "  未指定 -IncludeKnowledge，知识状态允许为 BLOCKED_RAG_DATA。"
    }

    Write-Host "[5/5] 输出安全摘要..."
    & uv run sellpilot-check-demo-readiness
    if ($LASTEXITCODE -ne 0) {
        throw "最终就绪检查失败。"
    }
}
finally {
    Pop-Location
}
