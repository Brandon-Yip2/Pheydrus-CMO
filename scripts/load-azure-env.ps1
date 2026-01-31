# PowerShell Script to Load Azure Environment Variables
# This script loads your Azure Developer CLI environment variables every time you develop locally
# Usage: .\scripts\load-azure-env.ps1
# Then: $env:AZURE_SEARCH_SERVICE, etc. will be available in your current session

# Set error action preference
$ErrorActionPreference = "Stop"

# Colors for output
$Green = "`e[32m"
$Yellow = "`e[33m"
$Red = "`e[31m"
$Reset = "`e[0m"

Write-Host "${Green}========================================" -NoNewline
Write-Host "Azure Environment Loader"
Write-Host "========================================${Reset}"

# Step 1: Check if azd is installed
Write-Host "${Yellow}[1/3]${Reset} Checking if Azure Developer CLI (azd) is installed..."
try {
    $azdVersion = azd version 2>$null
    Write-Host "${Green}✓${Reset} Azure Developer CLI found: $azdVersion"
} catch {
    Write-Host "${Red}✗${Reset} Azure Developer CLI not found. Please install it from: https://aka.ms/azd/install"
    exit 1
}

# Step 2: Get the default azd environment
Write-Host "${Yellow}[2/3]${Reset} Loading default Azure Developer CLI environment..."
try {
    $envListJson = azd env list -o json 2>$null | ConvertFrom-Json
    $defaultEnv = $envListJson | Where-Object { $_.IsDefault -eq $true }

    if (-not $defaultEnv) {
        Write-Host "${Red}✗${Reset} No default Azure Developer CLI environment found."
        Write-Host "Run 'azd env new' or 'azd env select' first."
        exit 1
    }

    $envName = $defaultEnv.Name
    $dotEnvPath = $defaultEnv.DotEnvPath
    Write-Host "${Green}✓${Reset} Found environment: ${Green}$envName${Reset}"
    Write-Host "${Green}✓${Reset} Loading from: $dotEnvPath"
} catch {
    Write-Host "${Red}✗${Reset} Failed to retrieve Azure Developer CLI environments: $_"
    exit 1
}

# Step 3: Load environment variables from .env file
Write-Host "${Yellow}[3/3]${Reset} Loading environment variables..."
try {
    if (-not (Test-Path $dotEnvPath)) {
        Write-Host "${Red}✗${Reset} Environment file not found at: $dotEnvPath"
        exit 1
    }

    $envVars = @{}
    Get-Content $dotEnvPath | ForEach-Object {
        $line = $_.Trim()
        # Skip empty lines and comments
        if ($line -and -not $line.StartsWith("#")) {
            $key, $value = $line -split '=', 2
            if ($key -and $value) {
                $envVars[$key.Trim()] = $value.Trim()
            }
        }
    }

    # Set environment variables in current process
    $envVars.GetEnumerator() | ForEach-Object {
        [Environment]::SetEnvironmentVariable($_.Key, $_.Value, "Process")
    }

    Write-Host "${Green}✓${Reset} Loaded ${Green}$($envVars.Count)${Reset} environment variables"

} catch {
    Write-Host "${Red}✗${Reset} Failed to load environment variables: $_"
    exit 1
}

# Summary
Write-Host ""
Write-Host "${Green}========================================" -NoNewline
Write-Host "Setup Complete!"
Write-Host "========================================${Reset}"
Write-Host ""
Write-Host "Key environment variables now available:"
Write-Host "  ${Green}AZURE_SEARCH_SERVICE${Reset}: $env:AZURE_SEARCH_SERVICE"
Write-Host "  ${Green}AZURE_SEARCH_INDEX${Reset}: $env:AZURE_SEARCH_INDEX"
Write-Host "  ${Green}AZURE_STORAGE_ACCOUNT${Reset}: $env:AZURE_STORAGE_ACCOUNT"
Write-Host "  ${Green}AZURE_OPENAI_SERVICE${Reset}: $env:AZURE_OPENAI_SERVICE"
Write-Host ""
Write-Host "You can now run your development commands:"
Write-Host "  ${Green}cd app/backend && python -m quart run --reload${Reset}"
Write-Host "  ${Green}cd app/frontend && npm run dev${Reset}"
Write-Host "  ${Green}python app/backend/prepdocs.py data/Train_CMO/**/*.pdf${Reset}"
Write-Host ""
