param(
    [switch]$Headless
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$godotExe = "C:\Users\Mike\Documents\Applications\Godot_v4.2.2-stable_win64.exe\Godot_v4.2.2-stable_win64.exe"
$dojoPath = Join-Path $repoRoot "dojo"
$projectFile = Join-Path $dojoPath "project.godot"

if (-not (Test-Path $godotExe)) {
    throw "Godot executable not found at '$godotExe'."
}

if (-not (Test-Path $projectFile)) {
    throw "Godot project file not found at '$projectFile'."
}

$godotArgs = @("--path", $dojoPath)

if ($Headless) {
    $godotArgs = @("--headless") + $godotArgs + @("--quit")
    Write-Host "Running AutomataValley Dojo headlessly for validation..."
    & $godotExe @godotArgs
    if ($?) {
        exit 0
    }
    exit 1
}

Write-Host "Launching AutomataValley Dojo..."
Write-Host "Godot: $godotExe"
Write-Host "Project: $dojoPath"

Start-Process -FilePath $godotExe -ArgumentList $godotArgs -WorkingDirectory $dojoPath
