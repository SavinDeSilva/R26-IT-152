$API = "http://192.168.1.96:5000"

$endpoints = @(
    "/health",
    "/sites",
    "/predict?site_id=1&date=2026-05-08",
    "/alert?site_id=1&date=2026-05-08",
    "/green-sites?date=2026-05-08",
    "/model-metrics",
    "/pipeline-status",
    "/best-times?site_id=1&month=5",
    "/flights"
)

foreach ($ep in $endpoints) {
    $url = "$API$ep"
    Write-Host "Testing $url ..." -NoNewline
    try {
        $response = Invoke-RestMethod -Uri $url -Method GET -TimeoutSec 5
        Write-Host " ✅ OK" -ForegroundColor Green
        Write-Host "   Response: $($response | ConvertTo-Json -Depth 2)" -ForegroundColor Gray
    } catch {
        Write-Host " ❌ FAILED" -ForegroundColor Red
        Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
    }
    Write-Host ""
}