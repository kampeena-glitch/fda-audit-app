$ActionFDA = New-ScheduledTaskAction -Execute "D:\app-fda-audit\run_fda_scraper.bat"
$TriggerFDA = New-ScheduledTaskTrigger -Daily -At 9:05am
$SettingsFDA = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$PrincipalFDA = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive
Register-ScheduledTask -TaskName "FDA_Scraper_Daily" -Action $ActionFDA -Trigger $TriggerFDA -Settings $SettingsFDA -Principal $PrincipalFDA -Force

$ActionMOPH = New-ScheduledTaskAction -Execute "D:\app-fda-audit\run_moph_scraper.bat"
$TriggerMOPH = New-ScheduledTaskTrigger -Daily -At 9:00am
$SettingsMOPH = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$PrincipalMOPH = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive
Register-ScheduledTask -TaskName "MOPH_Scraper_Daily" -Action $ActionMOPH -Trigger $TriggerMOPH -Settings $SettingsMOPH -Principal $PrincipalMOPH -Force
