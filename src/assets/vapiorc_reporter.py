import requests
import time
import socket
import subprocess
import logging
import os
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
WEBHOOK_HOST = "{{VAPIORC_HOST_IP}}"
WEBHOOK_PORT = "8000"
VM_TYPE = "11"
MAX_RETRIES = 30
RETRY_DELAY = 10

def get_mac_address():
    """Get the MAC address of the primary network interface"""
    try:
        output = subprocess.check_output("getmac", shell=True).decode('utf-8')
        # Parse the output and return the first valid MAC address
        for line in output.splitlines():
            if '-' in line:  # MAC addresses contain hyphens
                mac = line.split()[0]  # MAC address is usually the first element
                mac = mac.replace('-', ':')  # Replace '-' with ':'
                logger.info(f"Detected MAC address: {mac}")
                return mac
    except Exception as e:
        logger.error(f"Error getting MAC address: {e}")
    return None

def report_readiness():
    """Report container readiness to vapiorc webhook"""
    mac_address = get_mac_address()
    if not mac_address:
        logger.error("Could not determine MAC address")
        return False

    webhook_url = f"http://{WEBHOOK_HOST}:{WEBHOOK_PORT}/webhook/ready/{VM_TYPE}"
    headers = {"MAC-Address": mac_address}

    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"Reporting readiness to {webhook_url} (attempt {attempt + 1}/{MAX_RETRIES})")
            response = requests.post(webhook_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                logger.info("Successfully reported readiness")
                return True
            else:
                logger.warning(f"Webhook returned status {response.status_code}: {response.text}")
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to reach webhook: {e}")
            
        if attempt + 1 != MAX_RETRIES:
            logger.info(f"Waiting {RETRY_DELAY} seconds before retry...")
            time.sleep(RETRY_DELAY)
    
    logger.error(f"Failed to report readiness after {MAX_RETRIES} attempts")
    return False

if __name__ == "__main__":
    logger.info("Starting vapiorc readiness reporter")
    
    # Wait a bit for network to be fully ready
    time.sleep(30)
    
    # Report readiness
    if report_readiness():
        logger.info("Readiness reporting completed successfully")
    else:
        logger.error("Readiness reporting failed")