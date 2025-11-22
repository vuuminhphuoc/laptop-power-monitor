# Create desktop shortcut for Laptop Power Monitor

$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "Laptop Power Monitor.lnk"
$TargetPath = Join-Path $PSScriptRoot "run.bat"
$IconPath = "C:\Windows\System32\powercpl.dll"

$WScriptShell = New-Object -ComObject WScript.Shell
$Shortcut = $WScriptShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $TargetPath
$Shortcut.WorkingDirectory = $PSScriptRoot
$Shortcut.IconLocation = "$IconPath,1"
$Shortcut.Description = "Run Laptop Power Monitor"
$Shortcut.Save()

Write-Host "Shortcut created successfully on Desktop!" -ForegroundColor Green
Write-Host "Location: $ShortcutPath" -ForegroundColor Cyan
