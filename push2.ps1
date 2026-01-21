#!/usr/bin/env pwsh
$env:GIT_PAGER = "cat"
$env:PAGER = "cat"

Set-Location "d:\Projects\Trader"

Write-Host "Staging changes..."
& git add .

Write-Host "Creating commit..."
& git commit -m "Fix KeyError in live dashboard - use safe .get() for optional signal keys"

Write-Host "Pulling latest changes..."
& git pull origin main --ff-only 2>&1 | Select-Object -First 10

Write-Host "Pushing to GitHub..."
$result = & git push origin main 2>&1
Write-Host $result

Write-Host "Done!"
