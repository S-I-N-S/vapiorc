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

REM Create the readiness reporter script
echo Creating readiness reporter...
set "reporterPath=C:\Users\Docker\Desktop\vapiorc_reporter.py"

(
echo import requests
echo import time
echo import socket
echo import subprocess
echo import logging
echo import os
echo from pathlib import Path
echo.
echo # Configure logging
echo logging.basicConfig^(level=logging.INFO^)
echo logger = logging.getLogger^(__name__^)
echo.
echo # Configuration
echo WEBHOOK_HOST = "{{VAPIORC_HOST_IP}}"
echo WEBHOOK_PORT = "8000"
echo VM_TYPE = "11"
echo MAX_RETRIES = 30
echo RETRY_DELAY = 10
echo.
echo def get_mac_address^(^):
echo     """Get the MAC address of the primary network interface"""
echo     try:
echo         # Get MAC address using getmac command
echo         result = subprocess.run^(['getmac', '/fo', 'csv', '/nh'], capture_output=True, text=True^)
echo         if result.returncode == 0:
echo             # Parse the first MAC address from CSV output
echo             mac_line = result.stdout.strip^(^).split^('\n'^)[0]
echo             mac = mac_line.split^(','^)[0].strip^('"'^).replace^('-', ':'^)
echo             logger.info^(f"Detected MAC address: {mac}"^)
echo             return mac
echo     except Exception as e:
echo         logger.error^(f"Error getting MAC address: {e}"^)
echo     return None
echo.
echo def report_readiness^(^):
echo     """Report container readiness to vapiorc webhook"""
echo     mac_address = get_mac_address^(^)
echo     if not mac_address:
echo         logger.error^("Could not determine MAC address"^)
echo         return False
echo.
echo     webhook_url = f"http://{WEBHOOK_HOST}:{WEBHOOK_PORT}/webhook/ready/{VM_TYPE}"
echo     headers = {"MAC-Address": mac_address}
echo.
echo     for attempt in range^(MAX_RETRIES^):
echo         try:
echo             logger.info^(f"Reporting readiness to {webhook_url} ^(attempt {attempt + 1}/{MAX_RETRIES}^)"^)
echo             response = requests.post^(webhook_url, headers=headers, timeout=10^)
echo             
echo             if response.status_code == 200:
echo                 logger.info^("Successfully reported readiness"^)
echo                 return True
echo             else:
echo                 logger.warning^(f"Webhook returned status {response.status_code}: {response.text}"^)
echo                 
echo         except requests.exceptions.RequestException as e:
echo             logger.warning^(f"Failed to reach webhook: {e}"^)
echo             
echo         if attempt + 1 != MAX_RETRIES:
echo             logger.info^(f"Waiting {RETRY_DELAY} seconds before retry..."^)
echo             time.sleep^(RETRY_DELAY^)
echo     
echo     logger.error^(f"Failed to report readiness after {MAX_RETRIES} attempts"^)
echo     return False
echo.
echo if __name__ == "__main__":
echo     logger.info^("Starting vapiorc readiness reporter"^)
echo     
echo     # Wait a bit for network to be fully ready
echo     time.sleep^(30^)
echo     
echo     # Report readiness
echo     if report_readiness^(^):
echo         logger.info^("Readiness reporting completed successfully"^)
echo     else:
echo         logger.error^("Readiness reporting failed"^)
) > "%reporterPath%"

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