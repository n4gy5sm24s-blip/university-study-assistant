$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runtimeRoot = Join-Path $projectRoot "desktop-runtime"
$pythonRoot = Join-Path $runtimeRoot "python"
$packagesRoot = Join-Path $runtimeRoot "packages"
$cacheRoot = Join-Path $projectRoot ".tmp\desktop-runtime"
$pythonArchive = Join-Path $cacheRoot "python-3.12.10-embed-amd64.zip"
$pythonUrl = "https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip"

New-Item -ItemType Directory -Force -Path $pythonRoot, $packagesRoot, $cacheRoot | Out-Null

if (-not (Test-Path (Join-Path $pythonRoot "python.exe"))) {
    if (-not (Test-Path $pythonArchive)) {
        Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonArchive
    }
    Expand-Archive -LiteralPath $pythonArchive -DestinationPath $pythonRoot -Force
}

$pathFile = Join-Path $pythonRoot "python312._pth"
@(
    "python312.zip"
    "."
    "..\packages"
    "..\..\backend"
    "import site"
) | Set-Content -LiteralPath $pathFile -Encoding ASCII

$pipPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
& $pipPython -m pip install --upgrade --target $packagesRoot -r (Join-Path $projectRoot "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    throw "Desktop Python dependencies could not be prepared."
}
