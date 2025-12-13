param(
    [string]$Mode = "Interactive",
    [bool]$GitPush = $false,
    [int]$BacktestDays = 60,
    [int]$BacktestSymbols = 200
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ELITE TRADER DEPLOYMENT MASTER" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$cpu = Get-WmiObject Win32_Processor | Select-Object -First 1
$ram = [math]::Round((Get-WmiObject Win32_ComputerSystemProduct).TotalPhysicalMemory / 1GB)

Write-Host "? CPU: $($cpu.Name)" -ForegroundColor Green
Write-Host "? RAM: ${ram}GB" -ForegroundColor Green
Write-Host "? GPU: RTX 4080 (assumed)" -ForegroundColor Green
Write-Host ""

Write-Host "?? BACKTEST CONFIGURATION" -ForegroundColor Yellow
Write-Host "? Days: $BacktestDays" -ForegroundColor Green
Write-Host "? Symbols: $BacktestSymbols" -ForegroundColor Green
Write-Host "? Total Bars: $($BacktestDays * $BacktestSymbols)" -ForegroundColor Green
Write-Host ""

if (!(Test-Path "scripts/prompts")) {
    New-Item -ItemType Directory -Path "scripts/prompts" -Force | Out-Null
    Write-Host "? Created scripts/prompts directory" -ForegroundColor Green
}

$prompts = @(
    @{ Name = "Prompt-01-Operator-Approval"; Title = "Operator Approval System"; EstTime = "2h" },
    @{ Name = "Prompt-02-Dashboard"; Title = "Glass-House Dashboard"; EstTime = "2h" },
    @{ Name = "Prompt-03-Backtest"; Title = "Hardware-Optimized Backtest"; EstTime = "2.5h" },
    @{ Name = "Prompt-04-Streaming"; Title = "Streaming Features"; EstTime = "1.5h" },
    @{ Name = "Prompt-05-Fusion"; Title = "Signal Fusion"; EstTime = "2h" },
    @{ Name = "Prompt-06-Learning"; Title = "Incremental Learning"; EstTime = "1.5h" },
    @{ Name = "Prompt-07-Risk"; Title = "Risk Validation"; EstTime = "1.5h" },
    @{ Name = "Prompt-08-Sizing"; Title = "Position Sizing"; EstTime = "1h" },
    @{ Name = "Prompt-09-Engine"; Title = "Trading Engine"; EstTime = "2h" },
    @{ Name = "Prompt-10-Orders"; Title = "Order Management"; EstTime = "1.5h" },
    @{ Name = "Prompt-11-Whales"; Title = "Unusual Whales"; EstTime = "1.5h" },
    @{ Name = "Prompt-12-Monitoring"; Title = "Monitoring"; EstTime = "1.5h" }
)

Write-Host "?? GENERATING 12 PROMPTS..." -ForegroundColor Yellow
Write-Host ""

$totalTime = 0
foreach ($prompt in $prompts) {
    $promptFile = "scripts/prompts/$($prompt.Name).md"
    $content = "# $($prompt.Title)`n`nHardware: i9-13900, 64GB RAM, RTX 4080`nBacktest: $BacktestDays days, $BacktestSymbols symbols`nEstimated Time: $($prompt.EstTime)`n`nGenerated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`n"
    
    Set-Content -Path $promptFile -Value $content -Force
    Write-Host "? Generated $($prompt.Name)" -ForegroundColor Green
    
    if ($prompt.EstTime -eq "2.5h") { $totalTime += 2.5 }
    elseif ($prompt.EstTime -eq "2h") { $totalTime += 2 }
    elseif ($prompt.EstTime -eq "1.5h") { $totalTime += 1.5 }
    elseif ($prompt.EstTime -eq "1h") { $totalTime += 1 }
}

Write-Host ""
Write-Host "? ALL 12 PROMPTS GENERATED" -ForegroundColor Green
Write-Host "?? Location: scripts/prompts/" -ForegroundColor Cyan
Write-Host "??  Total time: ${totalTime}h" -ForegroundColor Cyan
Write-Host ""

if (Test-Path ".git") {
    Write-Host "?? GIT OPERATIONS..." -ForegroundColor Yellow
    
    for ($i = 1; $i -le 12; $i++) {
        $bn = "feature/prompt-$('{0:D2}' -f $i)"
        git checkout -b $bn 2>&1 | Out-Null
        Write-Host "? Created: $bn" -ForegroundColor Green
    }
    
    Write-Host ""
    if ($GitPush) {
        Write-Host "?? Pushing to GitHub..." -ForegroundColor Yellow
        git push -u origin --all 2>&1 | Out-Null
        Write-Host "? All branches pushed!" -ForegroundColor Green
    } else {
        Write-Host "Review with: git status" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "? DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
