# download_mockups.ps1 - Downloads all V3 mockup images and commits to repo
# Run from repo root: .\scripts\download_mockups.ps1
# Closes Issue #14

$ErrorActionPreference = 'Stop'
$imagesDir = 'docs/mockups-v3/images'

Write-Host '=== Downloading V3 Mockup Images ===' -ForegroundColor Cyan

# Create images directory
New-Item -ItemType Directory -Force -Path $imagesDir | Out-Null

$images = @(
    @{ Name = '01-patterns-screener.png'; Url = 'https://ppl-ai-code-interpreter-files.s3.amazonaws.com/web/direct-files/e1ec84fbe320c5a50a076e46fa340018/fcc32c86-8af0-47e2-b1eb-3866557ebb06/5e56bb20.png' },
    @{ Name = '02-sentiment-intelligence.png'; Url = 'https://ppl-ai-code-interpreter-files.s3.amazonaws.com/web/direct-files/e1ec84fbe320c5a50a076e46fa340018/3b264b83-3f92-46ec-990f-7f772fdf6d6e/b3ce9999.png' },
    @{ Name = '03-data-sources-monitor.png'; Url = 'https://ppl-ai-code-interpreter-files.s3.amazonaws.com/web/direct-files/e1ec84fbe320c5a50a076e46fa340018/ffe86514-6021-4a7e-a74b-a389b5e1c925/882a6716.png' },
    @{ Name = '04-settings.png'; Url = 'https://ppl-ai-code-interpreter-files.s3.amazonaws.com/web/direct-files/e1ec84fbe320c5a50a076e46fa340018/ffe86514-6021-4a7e-a74b-a389b5e1c925/e3e055e6.png' },
    @{ Name = '05-agent-command-center.png'; Url = 'https://user-gen-media-assets.s3.amazonaws.com/gemini_images/5042afa9-4988-47cf-b755-879ee8da856e.png' }
)

foreach ($img in $images) {
    $outPath = Join-Path $imagesDir $img.Name
    Write-Host "Downloading $($img.Name)..." -NoNewline
    try {
        Invoke-WebRequest -Uri $img.Url -OutFile $outPath
        $size = (Get-Item $outPath).Length / 1KB
        Write-Host " OK ($([math]::Round($size))KB)" -ForegroundColor Green
    } catch {
        Write-Host " FAILED: $_" -ForegroundColor Red
    }
}

Write-Host "`n=== Committing to git ===" -ForegroundColor Cyan
git add $imagesDir
git commit -m 'docs: Add 5 mockup PNG files for permanent storage (closes #14)'
git push

Write-Host "`nDone! All 5 mockup images committed to $imagesDir" -ForegroundColor Green
