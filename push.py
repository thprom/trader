#!/usr/bin/env python3
import subprocess
import os

os.chdir(r'd:\Projects\Trader')

# Disable pager
env = os.environ.copy()
env['GIT_PAGER'] = 'cat'
env['PAGER'] = 'cat'

try:
    # Add files
    print("Adding files...")
    subprocess.run(['git', 'add', 'live_dashboard.py', 'final/live_dashboard.py'], 
                   env=env, check=True)
    
    # Commit
    print("Committing...")
    result = subprocess.run(['git', 'commit', '-m', 'Fix KeyError - safe signal dict access'],
                          env=env, capture_output=True, text=True)
    print(result.stdout)
    print(result.stderr)
    
    # Push
    print("Pushing...")
    result = subprocess.run(['git', 'push', 'origin', 'main'],
                          env=env, capture_output=True, text=True)
    print(result.stdout)
    print(result.stderr)
    
    print("✓ Push completed successfully!")
    
except subprocess.CalledProcessError as e:
    print(f"✗ Error: {e}")
    print(e.stdout)
    print(e.stderr)
