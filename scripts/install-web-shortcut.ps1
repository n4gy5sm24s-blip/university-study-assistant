$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$launcher = Join-Path $projectRoot "scripts\launch-web.ps1"
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "Open Coursework AI.lnk"
$powershell = Join-Path $PSHOME "powershell.exe"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $powershell
$shortcut.Arguments = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$launcher`""
$shortcut.WorkingDirectory = $projectRoot
$shortcut.Description = "Start Coursework AI and open it in Google Chrome"
$shortcut.IconLocation = "$powershell,0"
$shortcut.Save()

Write-Output $shortcutPath
