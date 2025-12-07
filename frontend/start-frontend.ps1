Write-Host "🚀 Starting Frontend..." -ForegroundColor Cyan
if (-not (Test-Path "node_modules")) {
    npm install
}
npm run dev
