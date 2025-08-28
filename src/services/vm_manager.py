import subprocess
import socket
import logging
import uuid
import shutil
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any

from core.config import settings
from core.db import GoldenImage, VMInstance, SessionLocal

logger = logging.getLogger(__name__)

class VMManager:
    """Core VM management service"""
    
    def __init__(self):
        settings.ensure_directories()
    
    def find_available_port(self) -> Optional[int]:
        """Find an available port in the configured range"""
        for port in range(settings.PORT_RANGE_START, settings.PORT_RANGE_END):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                if s.connect_ex(('0.0.0.0', port)) != 0:
                    # Double-check by trying to bind to the port
                    try:
                        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                        test_socket.bind(('', port))
                        test_socket.close()
                        logger.debug(f"Found available port: {port}")
                        return port
                    except OSError:
                        logger.debug(f"Port {port} is busy")
                        continue
                else:
                    logger.debug(f"Port {port} is in use")
        logger.warning(f"No available ports found in range {settings.PORT_RANGE_START}-{settings.PORT_RANGE_END}")
        return None
    
    async def create_golden_image(self, vm_type: str = "11") -> str:
        """Create a golden image by starting a VM and waiting for Windows installation"""
        golden_id = str(uuid.uuid4())
        
        # Create database record
        db = SessionLocal()
        try:
            golden_image = GoldenImage(
                id=golden_id,
                vm_type=vm_type,
                status="creating"
            )
            db.add(golden_image)
            db.commit()
        finally:
            db.close()
        
        try:
            # Create golden image directory
            golden_path = Path(settings.GOLDEN_IMAGES_PATH) / golden_id
            golden_path.mkdir(parents=True, exist_ok=True)
            
            # Find available port
            port = self.find_available_port()
            if not port:
                raise Exception("No available ports")
            
            # Start golden image container
            container_name = f"vapiorc_golden_{golden_id}"
            cmd = [
                "docker", "run", "-d",
                "--name", container_name,
                "--network", settings.DOCKER_NETWORK,
                "-p", f"{port}:8006",
                "-e", f"VERSION={vm_type}",
                "-e", "DISK_FMT=qcow2",
                "-v", f"{golden_path}:/storage",
                "--device=/dev/kvm",
                "--device=/dev/net/tun",
                "--cap-add", "NET_ADMIN",
                "--stop-timeout", "120",
                "dockurr/windows"
            ]
            
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            container_id = result.stdout.strip()
            
            logger.info(f"Started golden image container {container_name} (ID: {container_id}) on port {port}")
            
            # Wait for installation completion (this is a simplified version)
            # In a real implementation, you'd monitor the installation progress
            
            return golden_id
            
        except Exception as e:
            # Update status to failed
            db = SessionLocal()
            try:
                golden_image = db.query(GoldenImage).filter(GoldenImage.id == golden_id).first()
                if golden_image:
                    golden_image.status = "failed"
                    db.commit()
            finally:
                db.close()
            raise e
    
    async def mark_golden_image_ready(self, golden_id: str):
        """Mark a golden image as ready and create preload template"""
        try:
            db = SessionLocal()
            try:
                golden_image = db.query(GoldenImage).filter(GoldenImage.id == golden_id).first()
                if not golden_image:
                    raise Exception(f"Golden image {golden_id} not found")
                
                # First, shutdown the golden image container
                container_name = f"vapiorc_golden_{golden_id}"
                logger.info(f"Shutting down golden image container {container_name}")
                try:
                    subprocess.run(["docker", "stop", container_name], check=True, capture_output=True)
                    subprocess.run(["docker", "rm", container_name], check=True, capture_output=True)
                    logger.info(f"Successfully shut down and removed container {container_name}")
                except subprocess.CalledProcessError as e:
                    logger.warning(f"Error shutting down container {container_name}: {e}")
                
                # Copy golden image to template for fast cloning
                golden_path = Path(settings.GOLDEN_IMAGES_PATH) / golden_id
                template_path = Path(settings.GOLDEN_IMAGES_PATH) / f"{golden_image.vm_type}_template"
                
                if not golden_path.exists():
                    raise Exception(f"Golden image path {golden_path} does not exist")
                
                if template_path.exists():
                    shutil.rmtree(template_path)
                
                logger.info(f"Copying golden image from {golden_path} to {template_path}")
                shutil.copytree(golden_path, template_path)
                
                golden_image.status = "ready"
                db.commit()
                
                logger.info(f"Golden image {golden_id} marked as ready and template created")
            finally:
                db.close()
                
            # Only create hot spares if configured count > 0
            if settings.HOT_SPARE_COUNT > 0:
                logger.info(f"Creating {settings.HOT_SPARE_COUNT} hot spares")
                await self.ensure_hot_spares()
            else:
                logger.info("Hot spare count is 0, skipping hot spare creation")
                
        except Exception as e:
            logger.error(f"Error marking golden image ready: {e}")
            raise
    
    async def create_vm_instance(self, vm_type: str = "11", is_hot_spare: bool = False) -> str:
        """Create a new VM instance from golden image"""
        instance_id = str(uuid.uuid4())
        
        # Create database record
        db = SessionLocal()
        try:
            vm_instance = VMInstance(
                id=instance_id,
                vm_type=vm_type,
                status="starting",
                is_hot_spare=is_hot_spare
            )
            db.add(vm_instance)
            db.commit()
        finally:
            db.close()
        
        try:
            # Create instance directory
            instance_path = Path(settings.INSTANCES_PATH) / instance_id
            instance_path.mkdir(parents=True, exist_ok=True)
            
            # Copy from template
            template_path = Path(settings.GOLDEN_IMAGES_PATH) / f"{vm_type}_template"
            if not template_path.exists():
                raise Exception(f"No golden image template for {vm_type}")
            
            # Fast copy using hardlinks where possible
            for item in template_path.rglob('*'):
                if item.is_file():
                    relative = item.relative_to(template_path)
                    dest = instance_path / relative
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest)
            
            # Find available port
            port = self.find_available_port()
            if not port:
                raise Exception("No available ports")
            
            # Start VM container
            container_name = f"vapiorc_vm_{instance_id}"
            cmd = [
                "docker", "run", "-d",
                "--name", container_name,
                "--network", settings.DOCKER_NETWORK,
                "-p", f"{port}:8006",
                "-p", f"{port + 1000}:3389",  # RDP port
                "-e", f"VERSION={vm_type}",
                "-e", "DISK_FMT=qcow2",
                "-v", f"{instance_path}:/storage",
                "--device=/dev/kvm",
                "--device=/dev/net/tun",
                "--cap-add", "NET_ADMIN",
                "--stop-timeout", "120",
                "dockurr/windows"
            ]
            
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            container_id = result.stdout.strip()
            
            # Update database record
            db = SessionLocal()
            try:
                vm_instance = db.query(VMInstance).filter(VMInstance.id == instance_id).first()
                if vm_instance:
                    vm_instance.container_id = container_id
                    vm_instance.port = port
                    vm_instance.status = "ready"
                    db.commit()
            finally:
                db.close()
            
            logger.info(f"Started VM instance {instance_id} on port {port}")
            return instance_id
            
        except Exception as e:
            # Update status to failed and cleanup
            db = SessionLocal()
            try:
                vm_instance = db.query(VMInstance).filter(VMInstance.id == instance_id).first()
                if vm_instance:
                    vm_instance.status = "failed"
                    db.commit()
            finally:
                db.close()
            await self.cleanup_vm_instance(instance_id)
            raise e
    
    async def assign_vm(self, assigned_to: str) -> Optional[Dict[str, Any]]:
        """Assign a hot spare VM to a user/task"""
        db = SessionLocal()
        try:
            # Find available hot spare
            vm = db.query(VMInstance).filter(
                VMInstance.is_hot_spare == True,
                VMInstance.status == "ready",
                VMInstance.assigned_to.is_(None)
            ).first()
            
            if not vm:
                # No hot spares available, create one
                instance_id = await self.create_vm_instance(is_hot_spare=False)
                vm = db.query(VMInstance).filter(VMInstance.id == instance_id).first()
            
            if vm:
                vm.assigned_to = assigned_to
                vm.is_hot_spare = False
                vm.status = "busy"
                db.commit()
                
                # Ensure hot spare pool is replenished
                await self.ensure_hot_spares()
                
                return {
                    "instance_id": vm.id,
                    "container_id": vm.container_id,
                    "port": vm.port,
                    "novnc_url": f"http://localhost:{vm.port}",
                    "rdp_port": vm.port + 1000
                }
        finally:
            db.close()
        
        return None
    
    async def release_vm(self, instance_id: str):
        """Release a VM by completely destroying it for security reasons"""
        logger.info(f"Releasing VM {instance_id} by destroying it for security")
        await self.destroy_vm(instance_id)
        
        # Ensure hot spare pool is replenished after destroying a VM
        await self.ensure_hot_spares()
    
    async def destroy_vm(self, instance_id: str):
        """Completely destroy a VM instance"""
        await self.cleanup_vm_instance(instance_id)
        
        db = SessionLocal()
        try:
            vm = db.query(VMInstance).filter(VMInstance.id == instance_id).first()
            if vm:
                db.delete(vm)
                db.commit()
        finally:
            db.close()
        
        logger.info(f"Destroyed VM instance {instance_id}")
    
    async def cleanup_vm_instance(self, instance_id: str):
        """Clean up VM instance resources"""
        try:
            # Stop and remove container
            container_name = f"vapiorc_vm_{instance_id}"
            subprocess.run(["docker", "stop", container_name], check=False, capture_output=True)
            subprocess.run(["docker", "rm", container_name], check=False, capture_output=True)
            
            # Remove instance directory
            instance_path = Path(settings.INSTANCES_PATH) / instance_id
            if instance_path.exists():
                shutil.rmtree(instance_path)
                
        except Exception as e:
            logger.error(f"Error cleaning up VM instance {instance_id}: {e}")
    
    async def ensure_hot_spares(self):
        """Ensure we have the configured number of hot spares"""
        db = SessionLocal()
        try:
            current_count = db.query(VMInstance).filter(
                VMInstance.is_hot_spare == True,
                VMInstance.status == "ready",
                VMInstance.assigned_to.is_(None)
            ).count()
            
            needed = settings.HOT_SPARE_COUNT - current_count
            logger.info(f"Current hot spares: {current_count}, needed: {needed}")
            
            for i in range(needed):
                try:
                    logger.info(f"Creating hot spare {i + 1} of {needed}")
                    await self.create_vm_instance(is_hot_spare=True)
                    # Add delay between hot spare creation to prevent port conflicts
                    if i < needed - 1:  # Don't wait after the last one
                        await asyncio.sleep(2)
                except Exception as e:
                    logger.error(f"Error creating hot spare {i + 1}: {e}")
                    break
        finally:
            db.close()
    
    async def list_vms(self) -> List[Dict[str, Any]]:
        """List all VM instances"""
        db = SessionLocal()
        try:
            vms = db.query(VMInstance).all()
            return [
                {
                    "instance_id": vm.id,
                    "container_id": vm.container_id,
                    "vm_type": vm.vm_type,
                    "status": vm.status,
                    "port": vm.port,
                    "is_hot_spare": vm.is_hot_spare,
                    "assigned_to": vm.assigned_to,
                    "created_at": vm.created_at.isoformat() if vm.created_at else None
                }
                for vm in vms
            ]
        finally:
            db.close()