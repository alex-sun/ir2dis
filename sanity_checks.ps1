# Sanity checks for Windows/PowerShell friendly changes

Write-Host "Running sanity checks..." -ForegroundColor Green

# 1) Check for duplicate LOG_LEVEL in .env.example
Write-Host "`n1. Checking for duplicate LOG_LEVEL in .env.example..." -ForegroundColor Yellow
$logLevelCount = (Select-String .env.example -Pattern '^\s*LOG_LEVEL=').Length
if ($logLevelCount -eq 1) {
    Write-Host "✓ LOG_LEVEL appears only once in .env.example" -ForegroundColor Green
} else {
    Write-Host "✗ LOG_LEVEL appears $logLevelCount times in .env.example" -ForegroundColor Red
}

# 2) Check README shows PowerShell & 'docker compose'
Write-Host "`n2. Checking README for PowerShell and docker compose..." -ForegroundColor Yellow
$readmeContent = Get-Content README.md -Raw
if ($readmeContent -match "Copy-Item" -and $readmeContent -match "docker compose") {
    Write-Host "✓ README uses PowerShell and 'docker compose'" -ForegroundColor Green
} else {
    Write-Host "✗ README doesn't match expected PowerShell/docker compose format" -ForegroundColor Red
}

# 3) Check README has correct slash commands and env names
Write-Host "`n3. Checking README for correct slash commands and env names..." -ForegroundColor Yellow
if ($readmeContent -match "/set_channel" -and $readmeContent -match "/list_tracked" -and $readmeContent -match "IRACING_EMAIL" -and $readmeContent -match "IRACING_PASSWORD") {
    Write-Host "✓ README has correct slash commands and env names" -ForegroundColor Green
} else {
    Write-Host "✗ README missing expected slash commands or env names" -ForegroundColor Red
}

# 4) Check .gitignore no longer ignores source dirs
Write-Host "`n4. Checking .gitignore for source directory ignores..." -ForegroundColor Yellow
$gitIgnoreContent = Get-Content .gitignore -Raw
if ($gitIgnoreContent -match "^src/storage/\*") {
    Write-Host "✗ .gitignore still ignores src/storage/*" -ForegroundColor Red
} else {
    Write-Host "✓ .gitignore no longer ignores source directories" -ForegroundColor Green
}

Write-Host "`nSanity checks complete!" -ForegroundColor Green
