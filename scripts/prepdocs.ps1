#!/usr/bin/env pwsh

# Load Python environment
./scripts/load_python_env.ps1

$venvPythonPath = "./.venv/scripts/python.exe"
if (Test-Path -Path "/usr") {
    # fallback to Linux venv path
    $venvPythonPath = "./.venv/bin/python"
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Config-Driven Index Creation System" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$cwd = (Get-Location)
$additionalArgs = ""
if ($args) {
    $additionalArgs = "$args"
}

# Path to configuration file
$configPath = "$cwd/data/index_config.json"

if (-not (Test-Path -Path $configPath)) {
    Write-Host "ERROR: index_config.json not found at $configPath" -ForegroundColor Red
    Write-Host "Running in single-index mode with default settings..." -ForegroundColor Yellow
    $dataArg = "`"$cwd/data/*`""
    $argumentList = "./app/backend/prepdocs.py $dataArg --verbose $additionalArgs"
    Write-Host $argumentList
    $process = Start-Process -FilePath $venvPythonPath -ArgumentList $argumentList -Wait -NoNewWindow -PassThru
    exit $process.ExitCode
}

# Read and parse the configuration file
Write-Host "Loading configuration from: $configPath" -ForegroundColor Green
$config = Get-Content -Path $configPath -Raw | ConvertFrom-Json

$basePath = $config.base_path
$indexes = $config.indexes

# Count total indexes
$indexNames = $indexes.PSObject.Properties.Name
$totalIndexes = $indexNames.Count
$currentIndex = 0

Write-Host "Found $totalIndexes index(es) to create/update" -ForegroundColor Green
Write-Host "Base path: $basePath" -ForegroundColor Green
Write-Host ""

# Process each index defined in the config
foreach ($indexKey in $indexNames) {
    $currentIndex++
    $indexConfig = $indexes.$indexKey
    $indexName = $indexConfig.name
    $indexDescription = $indexConfig.description
    $folders = $indexConfig.folders

    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "[$currentIndex/$totalIndexes] Processing: $indexKey" -ForegroundColor Cyan
    Write-Host "  Index Name: $indexName" -ForegroundColor White
    Write-Host "  Description: $indexDescription" -ForegroundColor Gray
    Write-Host "========================================" -ForegroundColor Cyan

    # Check if folders is ["*"] (all folders)
    if ($folders.Count -eq 1 -and $folders[0] -eq "*") {
        Write-Host "  Mode: ALL folders (wildcard)" -ForegroundColor Yellow
        Write-Host ""

        $dataPath = "$cwd/$basePath/*"
        $argumentList = "./app/backend/prepdocs.py `"$dataPath`" --index $indexKey --verbose $additionalArgs"

        Write-Host "  Running: $argumentList" -ForegroundColor Gray
        $process = Start-Process -FilePath $venvPythonPath -ArgumentList $argumentList -Wait -NoNewWindow -PassThru

        if ($process.ExitCode -ne 0) {
            Write-Host "  ERROR: Failed to index all folders for $indexKey (exit code: $($process.ExitCode))" -ForegroundColor Red
            exit 1
        }
        Write-Host "  SUCCESS: All folders indexed to $indexName" -ForegroundColor Green
    }
    else {
        # Specific folders - loop through each one
        Write-Host "  Mode: Specific folders ($($folders.Count) folder(s))" -ForegroundColor Yellow
        Write-Host ""

        $folderCount = 0
        $totalFolders = $folders.Count

        foreach ($folder in $folders) {
            $folderCount++
            Write-Host "  [$folderCount/$totalFolders] Indexing folder: $folder" -ForegroundColor White

            $dataPath = "$cwd/$basePath/$folder"
            $argumentList = "./app/backend/prepdocs.py `"$dataPath`" --index $indexKey --verbose $additionalArgs"

            Write-Host "    Running: $argumentList" -ForegroundColor Gray
            $process = Start-Process -FilePath $venvPythonPath -ArgumentList $argumentList -Wait -NoNewWindow -PassThru

            if ($process.ExitCode -ne 0) {
                Write-Host "    ERROR: Failed to index folder '$folder' for $indexKey (exit code: $($process.ExitCode))" -ForegroundColor Red
                exit 1
            }
            Write-Host "    SUCCESS: '$folder' indexed to $indexName" -ForegroundColor Green
            Write-Host ""
        }
    }

    Write-Host ""
}

# Final summary
Write-Host "========================================" -ForegroundColor Green
Write-Host "  INDEXING COMPLETE!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Created/Updated indexes:" -ForegroundColor White

foreach ($indexKey in $indexNames) {
    $indexConfig = $indexes.$indexKey
    $indexName = $indexConfig.name
    $folders = $indexConfig.folders

    if ($folders.Count -eq 1 -and $folders[0] -eq "*") {
        Write-Host "  - $indexName ($indexKey): ALL folders" -ForegroundColor Cyan
    }
    else {
        Write-Host "  - $indexName ($indexKey): $($folders.Count) folder(s)" -ForegroundColor Cyan
    }
}

Write-Host ""
Write-Host "To switch indexes, set environment variable:" -ForegroundColor Yellow
Write-Host "  `$env:AZURE_SEARCH_INDEX = 'gptkbindex-internal'" -ForegroundColor Gray
Write-Host "  `$env:AZURE_SEARCH_INDEX = 'gptkbindex-public'" -ForegroundColor Gray
Write-Host ""
