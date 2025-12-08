<#
.SYNOPSIS
    Fix models.py Syntax Error
.DESCRIPTION
    Repairs the escaped newline characters in models.py
#>

Write-Host "`nFixing models.py syntax error..." -ForegroundColor Yellow

$modelsPath = "database\models.py"

if (!(Test-Path $modelsPath)) {
    Write-Host "ERROR: models.py not found!" -ForegroundColor Red
    exit 1
}

# Read the file
$content = Get-Content $modelsPath -Raw

# Check if it has the issue
if ($content -match '\\n') {
    Write-Host "Found escaped newlines - fixing..." -ForegroundColor Yellow
    
    # Replace literal \n with actual newlines
    $fixed = $content -replace '\\n', "`n"
    
    # Write back
    $fixed | Set-Content $modelsPath -Encoding UTF8 -NoNewline
    
    Write-Host "SUCCESS: models.py fixed!" -ForegroundColor Green
} else {
    Write-Host "No issues found in models.py" -ForegroundColor Green
}

# Test import
Write-Host "Testing import..." -ForegroundColor Yellow

try {
    python -c "from database.models import SymbolUniverse; print('✅ Import successful')"
    Write-Host "SUCCESS: models.py is working!" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Import still failing" -ForegroundColor Red
    Write-Host "$_" -ForegroundColor Red
    exit 1
}

Write-Host "`nmodels.py is now fixed and ready to use!`n" -ForegroundColor Green
