$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$releaseRoot = Join-Path $projectRoot "release-portable"
$appRoot = Join-Path $releaseRoot "Coursework AI"
$electronRoot = Join-Path $projectRoot "node_modules\electron\dist"
$zipPath = Join-Path $releaseRoot "Coursework-AI-Windows-0.1.0.zip"

if (-not (Test-Path (Join-Path $electronRoot "electron.exe"))) {
    throw "Electron runtime is missing. Run npm install first."
}

if (Test-Path $appRoot) {
    $resolvedRelease = (Resolve-Path $releaseRoot).Path
    $resolvedApp = (Resolve-Path $appRoot).Path
    if (-not $resolvedApp.StartsWith($resolvedRelease + [IO.Path]::DirectorySeparatorChar)) {
        throw "Refusing to replace a directory outside release-portable."
    }
    $emptyRoot = Join-Path $projectRoot ".tmp\empty-portable"
    New-Item -ItemType Directory -Force -Path $emptyRoot | Out-Null
    & robocopy $emptyRoot $resolvedApp /MIR /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -ge 8) {
        throw "Old portable directory could not be cleared (robocopy exit code $LASTEXITCODE)."
    }
    Remove-Item -LiteralPath $resolvedApp -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $appRoot | Out-Null
Copy-Item -Path (Join-Path $electronRoot "*") -Destination $appRoot -Recurse -Force

$officialExecutable = Join-Path $appRoot "electron.exe"
$productExecutable = Join-Path $appRoot "Coursework AI.exe"
Move-Item -LiteralPath $officialExecutable -Destination $productExecutable

$resources = Join-Path $appRoot "resources"
$defaultApp = Join-Path $resources "default_app.asar"
if (Test-Path $defaultApp) {
    Remove-Item -LiteralPath $defaultApp -Force
}

$electronApp = Join-Path $resources "app"
$backend = Join-Path $resources "backend"
$runtime = Join-Path $resources "runtime"
New-Item -ItemType Directory -Force -Path $electronApp, $backend, $runtime | Out-Null
Copy-Item -LiteralPath (Join-Path $projectRoot "electron") -Destination $electronApp -Recurse -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "package.json") -Destination $electronApp -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "app") -Destination $backend -Recurse -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "web") -Destination $backend -Recurse -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "desktop-runtime\python") -Destination $runtime -Recurse -Force
$packagesDestination = Join-Path $runtime "packages"
& robocopy (Join-Path $projectRoot "desktop-runtime\packages") $packagesDestination /E /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) {
    throw "Desktop packages could not be copied (robocopy exit code $LASTEXITCODE)."
}

if (Test-Path $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}
Push-Location $releaseRoot
try {
    & tar.exe -a -c -f $zipPath "Coursework AI"
    if ($LASTEXITCODE -ne 0) {
        throw "Portable ZIP could not be created (tar exit code $LASTEXITCODE)."
    }
} finally {
    Pop-Location
}
Write-Output $zipPath
