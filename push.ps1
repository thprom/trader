#!/usr/bin/env pwsh
# Push changes to GitHub

Set-Location "d:\Projects\Trader"

# Stage changes
git add .

# Commit with message
git commit -m "Fix KeyError in live dashboard - use safe .get() for optional signal keys"

# Pull latest
git pull origin main --ff-only 2>$null

# Push to GitHub
git push origin main

Write-Host "Push completed!"
