#!/usr/bin/env python3
"""
Git push script for Bybit Trading Bot
"""

import subprocess
import os
import sys

def run_command(cmd, cwd=None):
    """Execute a shell command and return output"""
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            cwd=cwd, 
            capture_output=True, 
            text=True,
            check=False
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)

def main():
    # Project directory
    project_dir = "/Users/danilapryadkoicloud.com/Documents/bybit-trading-bot/WORK IN THIS FOLDER"
    
    print("🚀 Initializing Git and Pushing to GitHub")
    print("=" * 50)
    
    # Change to project directory
    os.chdir(project_dir)
    print(f"📁 Working directory: {os.getcwd()}")
    
    # Initialize git if needed
    if not os.path.exists(".git"):
        print("📦 Initializing Git repository...")
        code, out, err = run_command("git init")
        if code == 0:
            print("✅ Git initialized")
        else:
            print(f"❌ Git init failed: {err}")
    
    # Configure git user
    print("⚙️ Configuring Git user...")
    run_command('git config user.email "danilapryadko@icloud.com"')
    run_command('git config user.name "Danila Pryadko"')
    print("✅ Git user configured")
    
    # Add remote
    print("📡 Adding remote origin...")
    code, out, err = run_command("git remote get-url origin")
    if code != 0:
        run_command("git remote add origin https://github.com/danilapryadko/bbBot.git")
        print("✅ Remote added")
    else:
        print("✅ Remote already exists")
    
    # Add all files
    print("📦 Adding files to staging...")
    run_command("git add .")
    
    # Check status
    code, out, err = run_command("git status --short")
    if out:
        print(f"Files to commit:\n{out}")
    
    # Create commit
    print("💾 Creating commit...")
    commit_msg = """Phase 0 Complete: Infrastructure ready with CI/CD

- Complete project structure
- Docker environment for local development  
- PostgreSQL database with schema
- GitHub Actions CI/CD pipeline
- Fly.io deployment configuration
- Health monitoring and metrics
- Automated testing setup
- Security scanning with Trivy
- Daily performance reports
- Telegram notifications support"""
    
    code, out, err = run_command(f'git commit -m "{commit_msg}"')
    if code == 0:
        print("✅ Commit created")
    elif "nothing to commit" in out or "nothing to commit" in err:
        print("ℹ️ No changes to commit")
    else:
        print(f"Commit output: {out}")
    
    # Create/switch to main branch
    print("🌿 Checking branch...")
    code, out, err = run_command("git branch --show-current")
    current_branch = out.strip()
    
    if not current_branch or current_branch != "main":
        print("Switching to main branch...")
        run_command("git checkout -b main")
        current_branch = "main"
    
    print(f"📌 Current branch: {current_branch}")
    
    # Push to GitHub
    print("\n📤 Pushing to GitHub...")
    print("This will push to: https://github.com/danilapryadko/bbBot")
    
    # Try regular push first
    code, out, err = run_command(f"git push -u origin {current_branch}")
    
    if code == 0:
        print("✅ Successfully pushed to GitHub!")
    else:
        print(f"Push output: {err}")
        print("\n⚠️ If this is the first push, you may need to use --force")
        print("Run: git push -u origin main --force")
    
    print("\n" + "=" * 50)
    print("🎉 Git operations complete!")
    print("\n📊 Repository: https://github.com/danilapryadko/bbBot")
    print("🔄 Actions: https://github.com/danilapryadko/bbBot/actions")
    print("\n📝 Next steps:")
    print("1. Check GitHub Actions status")
    print("2. Set up GitHub Secrets for CI/CD")
    print("3. Deploy to Fly.io")

if __name__ == "__main__":
    main()
