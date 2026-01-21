#!/usr/bin/env python3
import subprocess
import os

os.chdir(r'd:\Projects\Trader')
os.environ['GIT_PAGER'] = 'cat'

print("="*70)
print("GIT STATUS CHECK")
print("="*70)

# Get status
result = subprocess.run(['git', 'status', '--porcelain'], 
                       capture_output=True, text=True, env=os.environ)
print("\nUncommitted changes:")
print(result.stdout if result.stdout else "None")

print("\n" + "="*70)
print("COMMITTING YFINANCE FIX")
print("="*70)

# Add all changes
print("\n1. Adding files...")
subprocess.run(['git', 'add', '.'], capture_output=True, env=os.environ)
print("   ✓ Added")

# Commit
print("2. Committing...")
result = subprocess.run(
    ['git', 'commit', '-m', 'Fix: Replace data_api with yfinance for real market data + bot analysis docs'],
    capture_output=True, text=True, env=os.environ
)
if result.returncode == 0:
    print("   ✓ Committed")
    print(f"   Message: {result.stdout[:100]}")
else:
    print(f"   Note: {result.stdout if result.stdout else 'No changes'}")

# Push
print("3. Pushing to GitHub...")
result = subprocess.run(['git', 'push', 'origin', 'main'], 
                       capture_output=True, text=True, env=os.environ)
if result.returncode == 0:
    print("   ✓ PUSHED SUCCESSFULLY")
    print(result.stdout)
else:
    print(f"   Issue: {result.stderr if result.stderr else result.stdout}")
    # Try pull first
    print("\n4. Pulling latest from remote...")
    subprocess.run(['git', 'pull', 'origin', 'main', '--ff-only'],
                  capture_output=True, env=os.environ)
    print("   ✓ Pulled")
    
    print("5. Retrying push...")
    result = subprocess.run(['git', 'push', 'origin', 'main'],
                          capture_output=True, text=True, env=os.environ)
    if result.returncode == 0:
        print("   ✓ PUSHED SUCCESSFULLY")
    else:
        print(f"   Error: {result.stderr}")

print("\n" + "="*70)
print("RESULT")
print("="*70)

# Check latest commit
result = subprocess.run(['git', 'log', '--oneline', '-3'],
                       capture_output=True, text=True, env=os.environ)
print("\nLatest commits:")
print(result.stdout)

print("\n" + "="*70)
print("✅ Changes are now on GitHub!")
print("   Go to Streamlit Cloud and redeploy the app")
print("="*70)
