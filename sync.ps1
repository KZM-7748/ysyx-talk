# 一生一芯 签到同步：webhook.site -> npoint.io
# 用法：运行并保持窗口打开；签到前先运行「重置.bat」
$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$WEBHOOK_TOKEN = "07c078e9-36cc-4d4b-ba4e-bf603d959f34"
$NPOINT_ID = "bfc7f456872d12528f08"
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$RESET_FILE = Join-Path $SCRIPT_DIR "reset.txt"
$LOG_FILE = Join-Path $SCRIPT_DIR "sync-debug.log"
$GET_URL = "https://webhook.site/token/$WEBHOOK_TOKEN/requests?sorting=newest&per_page=100"
$PUT_URL = "https://api.npoint.io/$NPOINT_ID"

function Log($msg) {
  $line = "[$(Get-Date -Format 'HH:mm:ss')] $msg"
  Add-Content -Path $LOG_FILE -Value $line -Encoding UTF8
}

$resetAfter = 0

while ($true) {
  if (Test-Path $RESET_FILE) {
    $resetAfter = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
    Remove-Item $RESET_FILE -Force
    Log "RESET: cutoff_ms=$resetAfter"
    $emptyBytes = [System.Text.Encoding]::UTF8.GetBytes('{"names":[]}')
    Invoke-RestMethod -Method Post -Uri $PUT_URL -ContentType "application/json" -Body $emptyBytes -TimeoutSec 10 | Out-Null
  }

  try {
    $r = Invoke-RestMethod -Uri $GET_URL -Headers @{Accept='application/json'} -TimeoutSec 10
    $out = @()
    foreach ($item in $r.data) {
      # 用签到时自带的 t 参数（毫秒）过滤；没有 t 的旧记录跳过
      $t = 0
      if ($item.query -and $item.query.t) { [long]::TryParse([string]$item.query.t, [ref]$t) | Out-Null }
      if ($t -lt $resetAfter) { continue }
      $q = ($item.query | ConvertTo-Json -Compress)
      if ($q -match '"name":"(?<nm>[^"]+)"') { $out += $Matches.nm }
      $c = [string]$item.content
      if ($c -match '"name":"(?<nm2>[^"]+)"') { $out += $Matches.nm2 }
    }
    $u = @($out | Select-Object -Unique)

    $payload = '{"names":[' + (($u | ForEach-Object { '"' + ($_ -replace '"','\"') + '"' }) -join ',') + ']}'
    $payloadBytes = [System.Text.Encoding]::UTF8.GetBytes($payload)
    Invoke-RestMethod -Method Post -Uri $PUT_URL -ContentType "application/json" -Body $payloadBytes -TimeoutSec 10 | Out-Null

    Log "synced $($u.Count): $($u -join ', ')"
  } catch {
    Log "ERROR: $($_.Exception.Message)"
  }
  Start-Sleep -Seconds 3
}
