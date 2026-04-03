param(
    [ValidateSet("install", "dev", "test")]
    [string]$Command = "dev"
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendRoot = Split-Path -Parent $scriptDir
$venvDir = Join-Path $backendRoot ".venv"
$pythonExe = Join-Path $venvDir "Scripts\python.exe"
$requirementsFile = Join-Path $backendRoot "requirements.txt"
$envFile = Join-Path $backendRoot ".env"
$envExampleFile = Join-Path $backendRoot ".env.example"

function Ensure-Venv {
    $pipExe = Join-Path $venvDir "Scripts\pip.exe"

    if ((Test-Path $pythonExe) -and (Test-Path $pipExe)) {
        return
    }

    if (Test-Path $venvDir) {
        Write-Host "Detected incomplete .venv, recreating it"
        Remove-Item -Recurse -Force $venvDir
    }

    Write-Host "Creating virtual environment at $venvDir"
    Push-Location $backendRoot
    try {
        python -m venv .venv
    }
    finally {
        Pop-Location
    }
}

function Ensure-EnvFile {
    if ((Test-Path $envFile) -or (-not (Test-Path $envExampleFile))) {
        return
    }

    Copy-Item $envExampleFile $envFile
    Write-Host "Created .env from .env.example"
}

function Load-DotEnv {
    if (-not (Test-Path $envFile)) {
        return
    }

    foreach ($rawLine in Get-Content $envFile) {
        $line = $rawLine.Trim()
        if (($line -eq "") -or $line.StartsWith("#")) {
            continue
        }

        $pair = $line -split "=", 2
        if ($pair.Count -ne 2) {
            continue
        }

        $name = $pair[0].Trim()
        $value = $pair[1].Trim()
        [Environment]::SetEnvironmentVariable($name, $value, "Process")
    }
}

function Install-Backend {
    Ensure-Venv
    Ensure-EnvFile
    & $pythonExe -m pip install -r $requirementsFile
}

function Ensure-BackendDependencies {
    Ensure-Venv
    try {
        & $pythonExe -c "import fastapi, requests" *> $null
    }
    catch {
        Write-Host "Installing missing backend dependencies"
        Install-Backend
    }
}

function Start-Backend {
    Ensure-BackendDependencies
    Ensure-EnvFile
    Load-DotEnv

    Push-Location $backendRoot
    try {
        & $pythonExe -m uvicorn app.main:app --reload
    }
    finally {
        Pop-Location
    }
}

function Test-Backend {
    Ensure-BackendDependencies
    Ensure-EnvFile

    Push-Location $backendRoot
    try {
        & $pythonExe -m pytest
    }
    finally {
        Pop-Location
    }
}

switch ($Command) {
    "install" { Install-Backend }
    "dev" { Start-Backend }
    "test" { Test-Backend }
}
