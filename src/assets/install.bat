@echo off
REM Vapiorc Windows Post-Install Script
REM This script runs automatically after Windows installation completes
REM and sets up readiness reporting for both golden images and VM instances

echo Starting Vapiorc post-install configuration...

REM Copy this script to Desktop for troubleshooting (do this first in case of crashes)
copy "%~f0" "C:\Users\Docker\Desktop\install_debug.bat"

REM Check Windows version and set Python path
for /f "tokens=4-5 delims=. " %%i in ('ver') do set VERSION=%%i.%%j
echo Detected Windows version: %VERSION%

REM Install Python based on Windows version
if "%VERSION%" == "10.0" (
    echo Windows 10/11 detected, installing Python 3.12.3
    powershell -Command "Invoke-WebRequest -Uri https://www.python.org/ftp/python/3.12.3/python-3.12.3-amd64.exe -OutFile %temp%\python-installer.exe"
    powershell -Command "Start-Process -FilePath '%temp%\python-installer.exe' -ArgumentList '/quiet', 'InstallAllUsers=1', 'PrependPath=1' -Wait"
    set "pythonPath=C:\Program Files\Python312\python.exe"
) else (
    echo Unsupported Windows version: %VERSION%
    set "pythonPath=python"
)

REM Setup UTC time synchronization
echo Configuring time synchronization...
powershell -Command "Set-TimeZone -Id 'UTC'"
powershell -Command "w32tm /config /syncfromflags:manual /manualpeerlist:'time.windows.com,0.pool.ntp.org,1.pool.ntp.org,2.pool.ntp.org' /reliable:yes /update"
powershell -Command "Stop-Service w32time; Start-Service w32time"
powershell -Command "w32tm /resync /force"
powershell -Command "Set-Service -Name w32time -StartupType Automatic"

REM Install required Python packages
echo Installing Python dependencies...
powershell -Command "& '%pythonPath%' -m ensurepip"
powershell -Command "& '%pythonPath%' -m pip install requests psutil"

REM Copy the readiness reporter script from OEM folder
echo Copying readiness reporter script...
set "reporterPath=C:\Users\Docker\Desktop\vapiorc_reporter.py"
copy "C:\OEM\vapiorc_reporter.py" "%reporterPath%"

REM Replace the host IP placeholder in the copied script
echo Setting up host IP configuration...
powershell -Command "(Get-Content '%reporterPath%') -replace '{{VAPIORC_HOST_IP}}', (Get-NetRoute -DestinationPrefix '0.0.0.0/0' | Get-NetIPConfiguration | Where-Object {$_.IPv4DefaultGateway} | Select-Object -First 1).IPv4Address.IPAddress | Set-Content '%reporterPath%'"

REM Create a startup task that runs the reporter once the user logs in
echo Creating startup task...
set "taskName=VapiorcReadinessReporter"
set "scriptPath=C:\Users\Docker\Desktop\vapiorc_reporter.py"

REM Create the scheduled task to run on user logon with a delay
schtasks /create /tn "%taskName%" /tr "\"%pythonPath%\" \"%scriptPath%\"" /sc onlogon /rl HIGHEST /it /f /delay 0001:00

REM Also run the reporter immediately for golden image completion
echo Running immediate readiness check...
start /b powershell -Command "& '%pythonPath%' '%scriptPath%'"

echo Vapiorc post-install configuration completed.
echo The system will automatically report readiness to the vapiorc API.
echo Install script copied to Desktop as install_debug.bat for troubleshooting.