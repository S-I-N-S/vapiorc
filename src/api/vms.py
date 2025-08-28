from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import logging

from core.db import get_db
from services.vm_manager import VMManager

logger = logging.getLogger(__name__)
router = APIRouter()
vm_manager = VMManager()

@router.post("/golden-images", response_model=Dict[str, str])
async def create_golden_image(
    background_tasks: BackgroundTasks,
    vm_type: str = "11"
):
    """Create a new golden image"""
    try:
        golden_id = await vm_manager.create_golden_image(vm_type)
        
        # In a real implementation, you'd monitor the installation and automatically
        # mark it ready when Windows installation completes
        # For now, this is a manual process
        
        return {
            "golden_id": golden_id,
            "status": "creating",
            "message": "Golden image creation started. Monitor installation and call /golden-images/{golden_id}/ready when complete."
        }
    except Exception as e:
        logger.error(f"Error creating golden image: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/golden-images/{golden_id}/ready")
async def mark_golden_image_ready(golden_id: str):
    """Mark a golden image as ready for use"""
    try:
        await vm_manager.mark_golden_image_ready(golden_id)
        return {"status": "success", "message": "Golden image marked as ready"}
    except Exception as e:
        logger.error(f"Error marking golden image ready: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/instances", response_model=Dict[str, Any])
async def create_vm_instance(vm_type: str = "win11"):
    """Create a new VM instance"""
    try:
        instance_id = await vm_manager.create_vm_instance(vm_type)
        return {"instance_id": instance_id, "status": "creating"}
    except Exception as e:
        logger.error(f"Error creating VM instance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/assign", response_model=Dict[str, Any])
async def assign_vm(assigned_to: str):
    """Assign a VM to a user/task from hot spare pool"""
    try:
        vm_info = await vm_manager.assign_vm(assigned_to)
        if not vm_info:
            raise HTTPException(status_code=503, detail="No VMs available")
        return vm_info
    except Exception as e:
        logger.error(f"Error assigning VM: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/instances/{instance_id}/release")
async def release_vm(instance_id: str):
    """Release a VM by completely destroying it (for security - no data persistence)"""
    try:
        await vm_manager.release_vm(instance_id)
        return {"status": "success", "message": "VM destroyed for security (hot spares will be replenished)"}
    except Exception as e:
        logger.error(f"Error releasing VM: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/instances/{instance_id}")
async def destroy_vm(instance_id: str):
    """Completely destroy a VM instance"""
    try:
        await vm_manager.destroy_vm(instance_id)
        return {"status": "success", "message": "VM destroyed"}
    except Exception as e:
        logger.error(f"Error destroying VM: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/instances", response_model=List[Dict[str, Any]])
async def list_vms():
    """List all VM instances"""
    try:
        return await vm_manager.list_vms()
    except Exception as e:
        logger.error(f"Error listing VMs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/hot-spares/ensure")
async def ensure_hot_spares():
    """Manually trigger hot spare replenishment"""
    try:
        await vm_manager.ensure_hot_spares()
        return {"status": "success", "message": "Hot spare replenishment triggered"}
    except Exception as e:
        logger.error(f"Error ensuring hot spares: {e}")
        raise HTTPException(status_code=500, detail=str(e))