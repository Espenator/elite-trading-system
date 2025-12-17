# Test DNS resolution for fc.yahoo.com using different DNS servers

Write-Host "Testing DNS resolution for fc.yahoo.com" -ForegroundColor Cyan
Write-Host "=" * 60

Write-Host "`nCurrent DNS (your network):" -ForegroundColor Yellow
nslookup fc.yahoo.com

Write-Host "`n`nUsing Google DNS (8.8.8.8):" -ForegroundColor Yellow
nslookup fc.yahoo.com 8.8.8.8

Write-Host "`n`nUsing Cloudflare DNS (1.1.1.1):" -ForegroundColor Yellow
nslookup fc.yahoo.com 1.1.1.1

Write-Host "`n" + ("=" * 60)

