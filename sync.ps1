# 一生一芯 签到同步：webhook.site -> npoint.io
# 用法：运行并保持窗口打开；签到前先运行「重置.bat」
$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$WEBHOOK_TOKEN = "6e2a71b3-5582-4315-be38-390f9f541ddb"
$NPOINT_ID = "bfc7f456872d12528f08"
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$RESET_FILE = Join-Path $SCRIPT_DIR "reset.txt"
$GET_URL = "https://webhook.site/token/$WEBHOOK_TOKEN/requests?sorting=newest&per_page=100"
$PUT_URL = "https://api.npoint.io/$NPOINT_ID"

$resetAfter = 0

while ($true) {
  if (Test-Path $RESET_FILE) {
    $resetAfter = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
    Remove-Item $RESET_FILE -Force
    Write-Host "=== RESET: 名单已清空，仅统计新签到 ==="
    $emptyBytes = [System.Text.Encoding]::UTF8.GetBytes('{"names":[]}')
    Invoke-RestMethod -Method Post -Uri $PUT_URL -ContentType "application/json" -Body $emptyBytes -TimeoutSec 10 | Out-Null
  }

  try {
    $r = Invoke-RestMethod -Uri $GET_URL -Headers @{Accept='application/json'} -TimeoutSec 10
    $out = @()
    foreach ($item in $r.data) {
      if ($item.sorting -lt $resetAfter) { continue }
      $q = ($item.query | ConvertTo-Json -Compress)
      if ($q -match '"name":"(?<nm>[^"]+)"') { $out += $Matches.nm }
      $c = [string]$item.content
      if ($c -match '"name":"(?<nm2>[^"]+)"') { $out += $Matches.nm2 }
    }
    $u = @($out | Select-Object -Unique)

    $payload = '{"names":[' + (($u | ForEach-Object { '"' + ($_ -replace '"','\"') + '"' }) -join ',') + ']}'
    $payloadBytes = [System.Text.Encoding]::UTF8.GetBytes($payload)
    Invoke-RestMethod -Method Post -Uri $PUT_URL -ContentType "application/json" -Body $payloadBytes -TimeoutSec 10 | Out-Null

    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $($u.Count) 人"
  } catch {
    Write-Host "error: $($_.Exception.Message)"
  }
  Start-Sleep -Seconds 3
}
