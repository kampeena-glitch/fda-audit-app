$Action = New-ScheduledTaskAction -Execute "D:\app-fda-audit\run_fda_scraper.bat"
$Trigger = New-ScheduledTaskTrigger -Daily -At 9:05am
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive

Register-ScheduledTask -TaskName "FDA_Scraper_Daily" -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Force
