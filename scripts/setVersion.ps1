$version = (Select-String .\src\noelbundick\setup.py -Pattern "^VERSION = ""(.*)""").Matches.Groups[1].Value
Write-Host "##vso[task.setvariable variable=extensionVersion]$version"