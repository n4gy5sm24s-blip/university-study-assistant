$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$packages = Join-Path $projectRoot ".packages"
$database = Join-Path $projectRoot "data\study_assistant.db"
$environment = Join-Path $projectRoot ".env"
$url = "http://127.0.0.1:8000/"
$healthUrl = "http://127.0.0.1:8000/api/health"

function Test-CourseworkServer {
    try {
        $health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 1
        return $health.status -eq "ok"
    } catch {
        return $false
    }
}

if (-not (Test-Path $python)) {
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show(
        "The Coursework AI runtime is missing. Keep the complete project folder.",
        "Coursework AI could not start"
    ) | Out-Null
    exit 1
}

if (-not (Test-CourseworkServer)) {
    $env:PYTHONPATH = $packages
    $env:STUDY_ASSISTANT_DB = $database
    $env:STUDY_ASSISTANT_ENV = $environment
    Start-Process `
        -FilePath $python `
        -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" `
        -WorkingDirectory $projectRoot `
        -WindowStyle Hidden

    $ready = $false
    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        if (Test-CourseworkServer) {
            $ready = $true
            break
        }
        Start-Sleep -Milliseconds 250
    }
    if (-not $ready) {
        Add-Type -AssemblyName PresentationFramework
        [System.Windows.MessageBox]::Show(
            "The local server could not start. Make sure port 8000 is available.",
            "Coursework AI could not start"
        ) | Out-Null
        exit 1
    }
}

$chromeCandidates = @(
    (Join-Path $env:ProgramFiles "Google\Chrome\Application\chrome.exe"),
    (Join-Path ${env:ProgramFiles(x86)} "Google\Chrome\Application\chrome.exe"),
    (Join-Path $env:LOCALAPPDATA "Google\Chrome\Application\chrome.exe")
)
$chrome = $chromeCandidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if ($chrome) {
    Start-Process -FilePath $chrome -ArgumentList $url
} else {
    Start-Process $url
}
