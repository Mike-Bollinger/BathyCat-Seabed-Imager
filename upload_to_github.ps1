# BathyCat GitHub Upload Script
# Run this script in PowerShell to upload your project to GitHub

Write-Host "BathyCat Seabed Imager - GitHub Upload Script" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# Check if we're in the right directory
$currentDir = Get-Location
Write-Host "Current directory: $currentDir" -ForegroundColor Yellow

if (!(Test-Path "README.md") -or !(Test-Path "src")) {
    Write-Host "ERROR: This script must be run from the BathyCat project directory!" -ForegroundColor Red
    Write-Host "Please navigate to: C:\Users\mboll\OneDrive\Documents\Python\BathyCat Seabed Imager" -ForegroundColor Red
    pause
    exit 1
}

# Check if Git is installed
try {
    git --version | Out-Null
    Write-Host "✓ Git is installed" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Git is not installed or not in PATH!" -ForegroundColor Red
    Write-Host "Please install Git from: https://git-scm.com/download/win" -ForegroundColor Red
    pause
    exit 1
}

# Initialize Git repository if not already done
if (!(Test-Path ".git")) {
    Write-Host "Initializing Git repository..." -ForegroundColor Yellow
    git init
    Write-Host "✓ Git repository initialized" -ForegroundColor Green
} else {
    Write-Host "✓ Git repository already exists" -ForegroundColor Green
}

# Check Git configuration
$gitUser = git config user.name 2>$null
$gitEmail = git config user.email 2>$null

if (!$gitUser -or !$gitEmail) {
    Write-Host "Setting up Git configuration..." -ForegroundColor Yellow
    $userName = Read-Host "Enter your name for Git commits"
    $userEmail = Read-Host "Enter your email for Git commits"
    
    git config user.name "$userName"
    git config user.email "$userEmail"
    Write-Host "✓ Git configuration set" -ForegroundColor Green
}

# Add all files
Write-Host "Adding files to Git..." -ForegroundColor Yellow
git add .

# Check if there are any changes to commit
$status = git status --porcelain
if ($status) {
    Write-Host "✓ Files added to Git" -ForegroundColor Green
    
    # Commit changes
    Write-Host "Committing changes..." -ForegroundColor Yellow
    git commit -m "Initial commit: Complete BathyCat Seabed Imager system

Features:
- High-frequency underwater imaging (4+ FPS)
- GPS tagging and time synchronization
- Automated storage management
- Raspberry Pi 4 optimized
- Complete documentation and installation scripts"
    
    Write-Host "✓ Changes committed" -ForegroundColor Green
} else {
    Write-Host "ℹ No new changes to commit" -ForegroundColor Blue
}

# Add remote origin
$remoteUrl = "https://github.com/Mike-Bollinger/BathyCat-Seabed-Imager.git"
Write-Host "Adding GitHub remote..." -ForegroundColor Yellow

try {
    git remote add origin $remoteUrl 2>$null
    Write-Host "✓ Remote origin added" -ForegroundColor Green
} catch {
    # Remote might already exist
    git remote set-url origin $remoteUrl
    Write-Host "✓ Remote origin updated" -ForegroundColor Green
}

# Set main branch
Write-Host "Setting main branch..." -ForegroundColor Yellow
git branch -M main
Write-Host "✓ Main branch set" -ForegroundColor Green

# Push to GitHub
Write-Host "Pushing to GitHub..." -ForegroundColor Yellow
Write-Host "Note: You may be prompted for your GitHub credentials" -ForegroundColor Cyan

try {
    git push -u origin main
    Write-Host "✓ Successfully pushed to GitHub!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Your repository is now available at:" -ForegroundColor Cyan
    Write-Host "$remoteUrl" -ForegroundColor Blue
} catch {
    Write-Host "ERROR: Failed to push to GitHub!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Possible solutions:" -ForegroundColor Yellow
    Write-Host "1. Check your internet connection" -ForegroundColor White
    Write-Host "2. Verify the repository exists: $remoteUrl" -ForegroundColor White
    Write-Host "3. Check your GitHub credentials" -ForegroundColor White
    Write-Host "4. Try using GitHub Desktop instead" -ForegroundColor White
    Write-Host ""
    Write-Host "Manual commands to try:" -ForegroundColor Yellow
    Write-Host "git remote -v" -ForegroundColor White
    Write-Host "git push -u origin main" -ForegroundColor White
}

Write-Host ""
Write-Host "Upload script completed!" -ForegroundColor Cyan
pause
