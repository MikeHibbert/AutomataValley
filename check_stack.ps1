Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "== $Title =="
}

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Url
    )

    try {
        $response = Invoke-RestMethod -Uri $Url -Method Get -TimeoutSec 10
        Write-Host "[PASS] $Name -> $Url"
        return @{
            Name = $Name
            Url = $Url
            Ok = $true
            Body = $response
        }
    } catch {
        Write-Host "[FAIL] $Name -> $Url"
        Write-Host "       $($_.Exception.Message)"
        return @{
            Name = $Name
            Url = $Url
            Ok = $false
            Body = $null
        }
    }
}

Write-Section "Docker Compose"
docker compose -f docker/compose.yml ps

Write-Section "HTTP Health Checks"
$results = @(
    (Test-Endpoint -Name "Valley" -Url "http://localhost:8001/health")
    (Test-Endpoint -Name "Bridge" -Url "http://localhost:8002/health")
    (Test-Endpoint -Name "STT" -Url "http://localhost:8003/health")
    (Test-Endpoint -Name "TTS" -Url "http://localhost:8004/health")
    (Test-Endpoint -Name "Dojo Bootstrap" -Url "http://localhost:8002/api/bootstrap")
)

Write-Section "Ollama"
try {
    $ollamaTags = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 10
    $modelNames = @($ollamaTags.models | ForEach-Object { $_.name })
    if ($modelNames -contains "gemma3:latest") {
        Write-Host "[PASS] Ollama is reachable and gemma3:latest is available"
    } else {
        Write-Host "[WARN] Ollama is reachable but gemma3:latest was not found"
        if ($modelNames.Count -gt 0) {
            Write-Host "       Available models: $($modelNames -join ', ')"
        }
    }
} catch {
    Write-Host "[WARN] Could not reach local Ollama at http://localhost:11434"
    Write-Host "       $($_.Exception.Message)"
}

Write-Section "Summary"
$failedChecks = @($results | Where-Object { -not $_.Ok })
if ($failedChecks.Count -eq 0) {
    Write-Host "Core Docker services responded successfully."
    exit 0
}

Write-Host "One or more core service checks failed."
exit 1
