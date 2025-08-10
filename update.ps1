#!/usr/bin/env pwsh
<#
BathyCat Seabed Imager - Quick Update Script (Windows)
======================================================

Simple PowerShell script to update the BathyCat system from GitHub.
Run: .\update.ps1

Author: Mike Bollinger
Date: August 2025
#>

Write-Host "🚀 BathyCat Seabed Imager - Quick Update" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Check if we're in the right directory
if (-not (Test-Path "src\bathycat_imager.py")) {
    Write-Host "❌ Error: Not in BathyCat project directory" -ForegroundColor Red
    Write-Host "   Please run this script from the project root" -ForegroundColor Yellow
    exit 1
}

# Backup configuration
Write-Host "💾 Backing up configuration..." -ForegroundColor Yellow
if (Test-Path "config\bathycat_config.json") {
    Copy-Item "config\bathycat_config.json" "config\bathycat_config.json.backup"
    Write-Host "   Configuration backed up" -ForegroundColor Green
} else {
    Write-Host "   No configuration found" -ForegroundColor Gray
}

# Show current version
Write-Host "📍 Current version:" -ForegroundColor Yellow
git log --oneline -1

# Fetch and show what's new
Write-Host "🔍 Checking for updates..." -ForegroundColor Yellow
git fetch origin
$newCommits = (git log --oneline HEAD..origin/main | Measure-Object -Line).Lines

if ($newCommits -eq 0) {
    Write-Host "✅ Already up to date!" -ForegroundColor Green
    exit 0
}

Write-Host "📥 Found $newCommits new updates:" -ForegroundColor Cyan
git log --oneline HEAD..origin/main

# Pull updates
Write-Host "⬇️  Pulling updates..." -ForegroundColor Yellow
git pull origin main

# Update dependencies (if Python is available)
Write-Host "📦 Updating dependencies..." -ForegroundColor Yellow
try {
    pip install -r requirements.txt --user --quiet
    Write-Host "   Dependencies updated" -ForegroundColor Green
} catch {
    Write-Host "   Skipping dependencies (Python not configured)" -ForegroundColor Gray
}

# Restore configuration
Write-Host "🔧 Restoring configuration..." -ForegroundColor Yellow
if (Test-Path "config\bathycat_config.json.backup") {
    Copy-Item "config\bathycat_config.json.backup" "config\bathycat_config.json"
    Write-Host "   Configuration restored" -ForegroundColor Green
}

# Show new version
Write-Host "🎉 Updated to:" -ForegroundColor Green
git log --oneline -1

Write-Host ""
Write-Host "✨ Update complete!" -ForegroundColor Green
Write-Host "   Push changes to Pi with: git push origin main" -ForegroundColor Cyan
Write-Host "   Then run on Pi: ./update" -ForegroundColor Cyan
