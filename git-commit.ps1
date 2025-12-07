Write-Host "📦 GIT COMMIT HELPER" -ForegroundColor Cyan
git status --short
$message = Read-Host "Commit message (or cancel)"
if ($message -ne "cancel" -and $message -ne "") {
    git add .
    git commit -m "$message"
    $push = Read-Host "Push? [Y/n]"
    if ($push -ne "n") { git push origin main }
}
