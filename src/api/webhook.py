"""
Webhook endpoints for container lifecycle management
"""
import logging
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Response, status
from sqlalchemy.orm import Session

from core.config import settings
from core.db import SessionLocal, GoldenImage, VMInstance
from services.vm_manager import VMManager

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/ready/{vm_type}")
async def container_ready_webhook(
    vm_type: str,
    mac_address: Optional[str] = Header(None, alias="MAC-Address")
):
    """
    Webhook endpoint for containers to report they are ready.
    Called by install.bat script after Windows setup is complete.
    
    Args:
        vm_type: Windows version (10, 11, etc.)
        mac_address: MAC address of the container for identification
        
    Returns:
        dict: Status of the webhook processing
    """
    logger.info(f"Received readiness webhook from {vm_type} with MAC {mac_address}")
    
    if not mac_address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MAC-Address header is required"
        )
    
    # Find the container by MAC address
    container_info = await find_container_by_mac(vm_type, mac_address)
    
    if not container_info:
        logger.error(f"No container found for MAC {mac_address}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No container found for MAC address {mac_address}"
        )
    
    vm_manager = VMManager()
    
    if container_info["type"] == "golden_image":
        # Handle golden image completion
        logger.info(f"Processing golden image completion for {container_info['id']}")
        try:
            await vm_manager.mark_golden_image_ready(container_info["id"])
            # Automatically create hot spares now that template is ready
            await vm_manager.ensure_hot_spares()
            return {
                "status": "processed",
                "type": "golden_image",
                "message": f"Golden image {container_info['id']} marked as ready and hot spares initiated"
            }
        except Exception as e:
            logger.error(f"Error processing golden image webhook: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error processing golden image: {str(e)}"
            )
    
    elif container_info["type"] == "vm_instance":
        # Handle VM instance readiness
        logger.info(f"Processing VM instance readiness for {container_info['id']}")
        try:
            # Update VM status to ready
            db = SessionLocal()
            try:
                vm_instance = db.query(VMInstance).filter(VMInstance.id == container_info["id"]).first()
                if vm_instance and vm_instance.status == "starting":
                    vm_instance.status = "ready"
                    db.commit()
                    logger.info(f"VM instance {container_info['id']} marked as ready")
                    
                    return {
                        "status": "processed", 
                        "type": "vm_instance",
                        "message": f"VM instance {container_info['id']} marked as ready"
                    }
                else:
                    logger.warning(f"VM instance {container_info['id']} not found or not in starting state")
                    return {
                        "status": "ignored",
                        "message": "VM instance not in expected state"
                    }
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error processing VM instance webhook: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error processing VM instance: {str(e)}"
            )
    
    else:
        logger.error(f"Unknown container type: {container_info['type']}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unknown container type"
        )

@router.get("/status/{vm_type}")
async def container_status_check(
    vm_type: str,
    mac_address: Optional[str] = Header(None, alias="MAC-Address")
):
    """
    GET endpoint for containers to check if they are registered
    
    Args:
        vm_type: The VM type of the container
        mac_address: The MAC address of the container
        
    Returns:
        dict: Status message
    """
    logger.info(f"Received status check from {vm_type} with MAC {mac_address}")
    
    if not mac_address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MAC-Address header is required"
        )
    
    # Check if container is registered
    container_info = await find_container_by_mac(vm_type, mac_address)
    
    if container_info:
        return {
            "status": "registered",
            "type": container_info["type"],
            "id": container_info["id"]
        }
    
    # Not registered
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Container not registered"
    )

async def find_container_by_mac(vm_type: str, mac_address: str) -> Optional[dict]:
    """
    Find container information by MAC address using auto-generated .mac files from qemu/kvm
    
    Args:
        vm_type: The VM type to search in
        mac_address: The MAC address to search for
        
    Returns:
        Optional[dict]: Container info with id and type, or None if not found
    """
    try:
        mac_address = mac_address.strip().upper().replace('-', ':')
        
        # Check golden images first
        golden_path = Path(settings.GOLDEN_IMAGES_PATH)
        for golden_dir in golden_path.glob("*"):
            if not golden_dir.is_dir() or golden_dir.name.endswith("_template"):
                continue
                
            for mac_file in golden_dir.glob("*.mac"):
                if mac_file.exists():
                    try:
                        with open(mac_file, "r") as f:
                            stored_mac = f.read().strip().upper().replace('-', ':')
                        
                        if stored_mac == mac_address:
                            golden_id = golden_dir.name
                            logger.info(f"Found golden image {golden_id} for MAC {mac_address}")
                            return {"id": golden_id, "type": "golden_image"}
                    except Exception as e:
                        logger.warning(f"Error reading MAC file {mac_file}: {e}")
                        continue
        
        # Check VM instances
        instances_path = Path(settings.INSTANCES_PATH)
        for instance_dir in instances_path.glob("*"):
            if not instance_dir.is_dir():
                continue
                
            for mac_file in instance_dir.glob("*.mac"):
                if mac_file.exists():
                    try:
                        with open(mac_file, "r") as f:
                            stored_mac = f.read().strip().upper().replace('-', ':')
                        
                        if stored_mac == mac_address:
                            instance_id = instance_dir.name
                            logger.info(f"Found VM instance {instance_id} for MAC {mac_address}")
                            return {"id": instance_id, "type": "vm_instance"}
                    except Exception as e:
                        logger.warning(f"Error reading MAC file {mac_file}: {e}")
                        continue
        
        logger.info(f"No container found for MAC {mac_address}")
        return None
        
    except Exception as e:
        logger.error(f"Error finding container by MAC: {e}")
        return None