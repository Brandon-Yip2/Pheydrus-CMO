./scripts/load_python_env.ps1

$venvPythonPath = "./.venv/scripts/python.exe"
if (Test-Path -Path "/usr") {
  # fallback to Linux venv path
  $venvPythonPath = "./.venv/bin/python"
}

Write-Host 'Running "prepdocs_dual.py" - Config-driven dual-index document preparation'
Write-Host ''

# Default arguments
$additionalArgs = "--verbose"

# Parse command line arguments
if ($args) {
  $additionalArgs = "$additionalArgs $args"
}

$argumentList = "./app/backend/prepdocs_dual.py $additionalArgs"

Write-Host "Command: $venvPythonPath $argumentList"
Write-Host ''

Start-Process -FilePath $venvPythonPath -ArgumentList $argumentList -Wait -NoNewWindow
