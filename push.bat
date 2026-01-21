@echo off
cd /d d:\Projects\Trader
setlocal enabledelayedexpansion

echo Staging files...
git add live_dashboard.py final/live_dashboard.py

echo Committing changes...
git commit -m "Fix KeyError - safe signal dict access"

echo Pushing to GitHub...
git push origin main

echo Done!
pause
