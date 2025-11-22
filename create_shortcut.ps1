# Create desktop shortcut for Laptop Power Monitor

$ScriptPath = $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path $ScriptPath
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "Laptop Power Monitor.lnk"
$TargetPath = Join-Path $ProjectDir "run.bat"
$IconPath = "C:\Windows\System32\powercpl.dll"

Write-Host "Creating shortcut..."
Write-Host "Target: $TargetPath"

$WScriptShell = New-Object -ComObject WScript.Shell
$Shortcut = $WScriptShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $TargetPath
$Shortcut.WorkingDirectory = $ProjectDir
$Shortcut.IconLocation = "$IconPath,1"
$Shortcut.Description = "Run Laptop Power Monitor"
$Shortcut.Save()

Write-Host "✓ Shortcut created successfully on Desktop!" -ForegroundColor Green
Write-Host "  Location: $ShortcutPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
