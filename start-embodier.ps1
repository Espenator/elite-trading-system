param([switch]$SkipFrontend,[int]$BackendPort=0,[int]$FrontendPort=0,[int]$MaxRestarts=5)
$ErrorActionPreference="Continue"
$R=Split-Path -Parent $MyInvocation.MyCommand.Path;$BD="$R\backend";$FD="$R\frontend-v2";$LD="$R\logs"
if(!(Test-Path $LD)){New-Item -ItemType Directory $LD -Force|Out-Null}
$ef="$BD\.env"
function GE($k,$d){if(Test-Path $ef){$l=Get-Content $ef|Where-Object{$_ -match "^$k="};if($l){return($l -split "=",2)[1].Trim()}};$d}
if($BackendPort -eq 0){$BackendPort=[int](GE "PORT" "8000")}
if($FrontendPort -eq 0){$FrontendPort=[int](GE "FRONTEND_PORT" "3000")}
Write-Host ""
Write-Host "  EMBODIER TRADER - Backend::$BackendPort | Frontend::$FrontendPort" -ForegroundColor Magenta
Write-Host ""

# ── Aggressive cleanup: kill zombie python processes and free ports ──
Write-Host "  Cleaning up old processes..." -ForegroundColor Yellow
# Kill ALL python.exe processes to release DuckDB file locks
Get-Process -Name python -EA SilentlyContinue | Stop-Process -Force -EA SilentlyContinue
Get-Process -Name python3 -EA SilentlyContinue | Stop-Process -Force -EA SilentlyContinue
# Kill anything holding ports 8000 and 3000
@($BackendPort,$FrontendPort)|ForEach-Object{
    Get-NetTCPConnection -LocalPort $_ -EA SilentlyContinue | ForEach-Object {
        Stop-Process -Id $_.OwningProcess -Force -EA SilentlyContinue
    }
}
# Wait for DuckDB file lock release
Start-Sleep 3
Write-Host "  Cleanup done." -ForegroundColor Green

if(Test-Path $ef){$rb=[IO.File]::ReadAllBytes($ef);if($rb.Length -ge 3 -and $rb[0]-eq 0xEF -and $rb[1]-eq 0xBB -and $rb[2]-eq 0xBF){[IO.File]::WriteAllText($ef,[IO.File]::ReadAllText($ef,[Text.Encoding]::UTF8),(New-Object Text.UTF8Encoding($false)))}}
elseif(Test-Path "$BD\.env.example"){Copy-Item "$BD\.env.example" $ef}
@($BackendPort,$FrontendPort)|ForEach-Object{Get-NetTCPConnection -LocalPort $_ -EA SilentlyContinue|ForEach-Object{Stop-Process -Id $_.OwningProcess -Force -EA SilentlyContinue}};Start-Sleep 1
Set-Location $BD
if(!(Test-Path venv)){python -m venv venv}
& .\venv\Scripts\Activate.ps1
try{python -c "import fastapi" 2>&1|Out-Null}catch{};if($LASTEXITCODE-ne 0){pip install -r requirements.txt --quiet}
try{python -c "import aiohttp" 2>&1|Out-Null}catch{};if($LASTEXITCODE-ne 0){pip install aiohttp --quiet}
$bj=Start-Job -ScriptBlock{param($d,$p,$l,$m);Set-Location $d;& .\venv\Scripts\Activate.ps1;$env:PORT=$p;$env:PYTHONIOENCODING="utf-8";$env:PYTHONUNBUFFERED="1";$r=0;while($r-le$m){if($r-gt 0){"$(Get-Date -F 'HH:mm:ss') RESTART $r"|Tee-Object $l -Append;Start-Sleep 5};try{python start_server.py 2>&1|Tee-Object $l -Append}catch{"$_"|Tee-Object $l -Append};$r++}} -Arg $BD,$BackendPort,"$LD\backend.log",$MaxRestarts
Write-Host "Waiting for backend..." -ForegroundColor Cyan -NoNewline
$ok=$false;for($i=0;$i-lt 45;$i++){Start-Sleep 1;try{if((Invoke-WebRequest "http://localhost:$BackendPort/healthz" -TimeoutSec 2 -EA SilentlyContinue).StatusCode-eq 200){$ok=$true;break}}catch{};Write-Host "." -NoNewline}
Write-Host "";if($ok){Write-Host "[OK] Backend http://localhost:$BackendPort" -ForegroundColor Green}else{Write-Host "[WARN] Check $LD\backend.log" -ForegroundColor Yellow}
$fj=$null
if(!$SkipFrontend){Set-Location $FD;if(!(Test-Path node_modules)){npm install --silent}
$fj=Start-Job -ScriptBlock{param($d,$bp,$fp,$l,$m);Set-Location $d;$env:VITE_BACKEND_URL="http://localhost:$bp";$r=0;while($r-le$m){if($r-gt 0){"$(Get-Date -F 'HH:mm:ss') RESTART FE $r"|Tee-Object $l -Append;Start-Sleep 3};try{npx vite --port $fp --host 2>&1|Tee-Object $l -Append}catch{"$_"|Tee-Object $l -Append};$r++}} -Arg $FD,$BackendPort,$FrontendPort,"$LD\frontend.log",$MaxRestarts
Start-Sleep 3;Write-Host "[OK] Frontend http://localhost:$FrontendPort" -ForegroundColor Green
Start-Sleep 2;Start-Process "http://localhost:$FrontendPort"}
Write-Host ""
Write-Host "  RUNNING | Ctrl+C to stop" -ForegroundColor Green
Write-Host ""
try{while($true){Start-Sleep 10;if($bj.State-eq"Failed"){Write-Host "Backend FAILED" -ForegroundColor Red;Receive-Job $bj;break}}}finally{
if($bj){Stop-Job $bj -EA SilentlyContinue;Remove-Job $bj -EA SilentlyContinue}
if($fj){Stop-Job $fj -EA SilentlyContinue;Remove-Job $fj -EA SilentlyContinue}
@($BackendPort,$FrontendPort)|ForEach-Object{Get-NetTCPConnection -LocalPort $_ -EA SilentlyContinue|ForEach-Object{Stop-Process -Id $_.OwningProcess -Force -EA SilentlyContinue}}
Write-Host "[OK] Stopped." -ForegroundColor Green}
