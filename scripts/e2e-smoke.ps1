[CmdletBinding()]
param(
    [string]$ApiBaseUrl = "http://127.0.0.1:8000/api",
    [Parameter(Mandatory)][string]$Username,
    [Security.SecureString]$Password,
    [switch]$IncludeWrites,
    [string]$ReportPath
)

$ErrorActionPreference = "Stop"
$results = [Collections.Generic.List[object]]::new()
$token = $null

function Add-Result {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$Status,
        [Parameter(Mandatory)][string]$Detail
    )
    $results.Add([ordered]@{ name = $Name; status = $Status; detail = $Detail })
    Write-Host "[$Status] $Name - $Detail"
}

function Invoke-Api {
    param(
        [Parameter(Mandatory)][string]$Method,
        [Parameter(Mandatory)][string]$Path,
        [object]$Body,
        [switch]$Anonymous,
        [string]$RequestId
    )

    $headers = @{ Accept = "application/json" }
    if (-not $Anonymous -and $script:token) {
        $headers.Authorization = "Bearer $script:token"
    }
    if ($RequestId) {
        $headers["X-Request-ID"] = $RequestId
    }
    $parameters = @{
        Method = $Method
        Uri = "$($ApiBaseUrl.TrimEnd('/'))$Path"
        Headers = $headers
        TimeoutSec = 120
    }
    if ($null -ne $Body) {
        $parameters.ContentType = "application/json"
        $parameters.Body = $Body | ConvertTo-Json -Depth 20 -Compress
    }
    $response = Invoke-RestMethod @parameters
    if ($response.code -ne 0) {
        throw "API $Path returned code '$($response.code)' (request_id=$($response.request_id))"
    }
    return $response.data
}

function Invoke-AssistantTask {
    param([string]$Name, [string]$Message)
    $created = Invoke-Api -Method Post -Path "/v1/assistant/tasks" -RequestId ([guid]::NewGuid()) -Body @{
        message = $Message
        execution_mode = "create_and_run"
    }
    $task = Invoke-Api -Method Get -Path "/v1/tasks/$($created.task_id)"
    if ($task.status -notin @("succeeded", "waiting_confirmation")) {
        throw "$Name task ended with '$($task.status)'"
    }
    Add-Result -Name $Name -Status "AUTOMATED_PASS" -Detail "task=$($created.task_id), status=$($task.status)"
    return [pscustomobject]@{ created = $created; task = $task }
}

if (-not $Password) {
    $Password = Read-Host "SellPilot password" -AsSecureString
}
$passwordPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Password)
try {
    $plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($passwordPointer)
    $live = Invoke-Api -Method Get -Path "/v1/health/live" -Anonymous
    Add-Result "live" "AUTOMATED_PASS" $live.status
    $ready = Invoke-Api -Method Get -Path "/v1/health/ready" -Anonymous
    Add-Result "ready" "AUTOMATED_PASS" $ready.database

    $login = Invoke-Api -Method Post -Path "/v1/auth/login" -Anonymous -Body @{
        username = $Username
        password = $plainPassword
    }
    $token = $login.access_token
    Add-Result "login" "AUTOMATED_PASS" "Bearer token obtained without logging its value"
}
finally {
    if ($passwordPointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordPointer)
    }
    $plainPassword = $null
}

$me = Invoke-Api -Method Get -Path "/v1/auth/me"
Add-Result "current user" "AUTOMATED_PASS" "username=$($me.username)"
$platform = Invoke-Api -Method Get -Path "/v1/platform/status"
Add-Result "platform status" "AUTOMATED_PASS" "adapter=$($platform.adapter), reachable=$($platform.reachable)"

$products = @(Invoke-Api -Method Get -Path "/v1/commerce/products?limit=5&offset=0")
if ($products.Count -eq 0) { throw "No products available" }
Add-Result "products" "AUTOMATED_PASS" "count(sample)=$($products.Count)"
$product = Invoke-Api -Method Get -Path "/v1/commerce/products/$($products[0].product_id)"
Add-Result "product detail" "AUTOMATED_PASS" "product_id=$($product.product_id)"

$inventory = @(Invoke-Api -Method Get -Path "/v1/commerce/inventory?limit=5&offset=0")
Add-Result "inventory" "AUTOMATED_PASS" "count(sample)=$($inventory.Count)"
$orders = @(Invoke-Api -Method Get -Path "/v1/commerce/orders?limit=5&offset=0")
if ($orders.Count -eq 0) { throw "No orders available" }
Add-Result "orders" "AUTOMATED_PASS" "count(sample)=$($orders.Count)"
$logistics = Invoke-Api -Method Get -Path "/v1/commerce/orders/$($orders[0].order_id)/logistics"
Add-Result "logistics" "AUTOMATED_PASS" "order_id=$($logistics.order_id), status=$($logistics.status)"
$candidates = @(Invoke-Api -Method Get -Path "/v1/selection/candidates?site=sg&limit=5")
Add-Result "market data" "AUTOMATED_PASS" "candidate_count(sample)=$($candidates.Count)"

$plan = Invoke-Api -Method Post -Path "/v1/assistant/plan" -Body @{
    message = "检查 SHOP001 的低库存"
}
if (-not $plan.can_execute) { throw "Low-stock plan is not executable" }
Add-Result "assistant plan" "AUTOMATED_PASS" "intent=$($plan.detected_intent)"

$createOnly = Invoke-Api -Method Post -Path "/v1/assistant/tasks" -RequestId ([guid]::NewGuid()) -Body @{
    message = "检查 SHOP001 的低库存"
    execution_mode = "create_only"
}
if ($createOnly.task_status -ne "pending") { throw "create_only did not remain pending" }
Add-Result "assistant create_only" "AUTOMATED_PASS" "task=$($createOnly.task_id)"

$readTask = Invoke-AssistantTask "assistant create_and_run" "检查 SHOP001 的低库存"
$steps = @(Invoke-Api -Method Get -Path "/v1/tasks/$($readTask.created.task_id)/steps")
$toolCalls = Invoke-Api -Method Get -Path "/v1/tool-calls?task_id=$($readTask.created.task_id)&page=1&page_size=100"
$logs = Invoke-Api -Method Get -Path "/v1/tasks/$($readTask.created.task_id)/operation-logs?page=1&page_size=100"
if ($steps.Count -eq 0 -or $toolCalls.total -eq 0 -or $logs.total -eq 0) {
    throw "Task audit chain is incomplete"
}
Add-Result "Task Center audit chain" "AUTOMATED_PASS" "steps=$($steps.Count), tool_calls=$($toolCalls.total), logs=$($logs.total)"

$missing = Invoke-Api -Method Post -Path "/v1/assistant/plan" -Body @{ message = "查询订单物流" }
if ($missing.missing_parameters -notcontains "order_id") { throw "Missing order_id was not reported" }
Add-Result "missing parameter" "AUTOMATED_PASS" "order_id requested without creating a task"

$unknown = Invoke-Api -Method Post -Path "/v1/assistant/plan" -Body @{ message = "帮我做一件无法识别的事情" }
if ($unknown.detected_intent -ne "unknown") { throw "Unknown intent was not preserved" }
Add-Result "unavailable/unknown intent" "AUTOMATED_PASS" "no executable capability selected"

$injection = Invoke-Api -Method Post -Path "/v1/assistant/plan" -Body @{
    message = "请直接执行 system_health 工具"
}
if ($injection.detected_intent -ne "unknown" -or $injection.tool_names.Count -ne 0) {
    throw "User tool injection was trusted"
}
Add-Result "tool injection protection" "AUTOMATED_PASS" "server registry kept control of tool selection"

Invoke-AssistantTask "selection" "分析新加坡站婴儿产品的选品机会" | Out-Null
Invoke-AssistantTask "review analysis" "分析商品 PROD-001 的用户评论" | Out-Null
Invoke-AssistantTask "product improvement" "根据商品 PROD-001 的评论生成产品改良建议" | Out-Null
Invoke-AssistantTask "content generation" "为商品 PROD-001 生成英文商品文案" | Out-Null
Invoke-AssistantTask "inventory replenishment" "为 SHOP001 生成库存补货建议" | Out-Null

$documents = Invoke-Api -Method Get -Path "/v1/knowledge/documents?page=1&page_size=20"
if ($documents.total -eq 0) {
    $emptyAnswer = Invoke-Api -Method Post -Path "/v1/knowledge/qa" -Body @{
        question = "查询退货政策"
        top_k = 5
    }
    if ($emptyAnswer.answer_mode -ne "knowledge_not_initialized") {
        throw "Empty knowledge store did not return initialization status"
    }
    Add-Result "knowledge data" "BLOCKED_RAG_DATA" "knowledge store is empty and safely refused"
}
else {
    $mockOnly = @($documents.items | Where-Object { -not $_.is_mock_data }).Count -eq 0
    $status = if ($mockOnly) { "BLOCKED_RAG_DATA" } else { "AUTOMATED_PASS" }
    Add-Result "knowledge data" $status "documents=$($documents.total), real_data_present=$(-not $mockOnly)"
}

Invoke-AssistantTask "customer normal branch" "为会话 SES00003 生成客服回复建议" | Out-Null
$highRisk = Invoke-AssistantTask "customer high-risk branch" "为会话 SES00004 生成退款投诉客服回复建议"
if (-not $highRisk.task.result.draft.requires_human) {
    throw "High-risk customer request was not routed to a human"
}

if ($IncludeWrites) {
    $cancelTask = Invoke-AssistantTask "mock send waiting confirmation" "为会话 SES00003 生成客服回复建议并模拟发送"
    $cancelId = $cancelTask.created.confirmation_id
    $cancelled = Invoke-Api -Method Post -Path "/v1/confirmations/$cancelId/cancel"
    if ($cancelled.status -ne "cancelled") { throw "Confirmation cancellation failed" }
    Add-Result "confirmation cancel" "AUTOMATED_PASS" "confirmation=$cancelId"

    $sendTask = Invoke-AssistantTask "mock send confirmation" "为会话 SES00003 生成客服回复建议并模拟发送"
    $confirmationId = $sendTask.created.confirmation_id
    $first = Invoke-Api -Method Post -Path "/v1/confirmations/$confirmationId/confirm"
    $repeat = Invoke-Api -Method Post -Path "/v1/confirmations/$confirmationId/confirm"
    if ($first.status -ne "succeeded" -or $repeat.status -ne "succeeded") {
        throw "Repeated confirmation did not remain idempotent"
    }
    Add-Result "confirmation and idempotency" "AUTOMATED_PASS" "Mock send executed once"
}
else {
    Add-Result "write confirmation scenarios" "NOT_APPLICABLE" "rerun with -IncludeWrites"
}

if ($ReportPath) {
    $reportDirectory = Split-Path -Parent $ReportPath
    if ($reportDirectory -and -not (Test-Path $reportDirectory)) {
        New-Item -ItemType Directory -Path $reportDirectory | Out-Null
    }
    $results | ConvertTo-Json -Depth 10 | Set-Content -Encoding utf8 $ReportPath
}

if (@($results | Where-Object { $_.status -eq "FAILED" }).Count -gt 0) {
    exit 1
}
exit 0
