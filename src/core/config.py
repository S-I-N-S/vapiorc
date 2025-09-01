import os
from pathlib import Path
from typing import Optional

class Settings:
    """Simple configuration management for vapiorc"""
    
    PROJECT_NAME: str = "vapiorc - VM Orchestrator"
    VERSION: str = "0.1.0"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/vapiorcdb")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    
    # Host paths (absolute paths on the Docker host)
    HOST_BASE_DIR: str = os.getenv("VAPIORC_HOST_BASE_DIR", "/home/cayub/code/vapiorc")
    HOST_DATA_DIR: str = os.getenv("VAPIORC_HOST_DATA_DIR", f"{HOST_BASE_DIR}/app_data")
    HOST_GOLDEN_IMAGES_PATH: str = f"{HOST_DATA_DIR}/golden_images"
    HOST_INSTANCES_PATH: str = f"{HOST_DATA_DIR}/instances"
    HOST_ASSETS_PATH: str = f"{HOST_BASE_DIR}/src/assets"
    
    # Container paths (internal to vapiorc app container)
    CONTAINER_DATA_DIR: str = os.getenv("VAPIORC_CONTAINER_DATA_DIR", "/app/data")
    GOLDEN_IMAGES_PATH: str = f"{CONTAINER_DATA_DIR}/golden_images"
    INSTANCES_PATH: str = f"{CONTAINER_DATA_DIR}/instances"
    
    # Docker settings  
    DOCKER_NETWORK: str = os.getenv("VAPIORC_NETWORK", "vapiorc_vapiorc_network")
    
    # Port management
    PORT_RANGE_START: int = int(os.getenv("VAPIORC_PORT_START", "8001"))
    PORT_RANGE_END: int = int(os.getenv("VAPIORC_PORT_END", "8100"))
    
    # Hot spare settings
    HOT_SPARE_COUNT: int = int(os.getenv("VAPIORC_HOT_SPARES", "1"))
    
    # VM Configuration
    VM_TYPE: str = "11"  # Fixed to Windows 11
    
    # Host networking
    HOST_IP: str = os.getenv("VAPIORC_HOST_IP", "192.168.2.21")
    
    @classmethod
    def ensure_directories(cls):
        """Ensure all required directories exist"""
        for path in [cls.GOLDEN_IMAGES_PATH, cls.INSTANCES_PATH]:
            Path(path).mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def ensure_install_script_configured(cls):
        """Ensure install.bat has the correct host IP configured"""
        import logging
        logger = logging.getLogger(__name__)
        
        # Try multiple possible paths for install.bat
        possible_paths = [
            Path(cls.HOST_ASSETS_PATH) / "install.bat",
            Path("/src/assets") / "install.bat",  # Container internal path
            Path(__file__).resolve().parent.parent / "assets" / "install.bat"  # Relative to this file
        ]
        
        install_bat_path = None
        for path in possible_paths:
            if path.exists():
                install_bat_path = path
                logger.info(f"Found install.bat at: {path}")
                break
        
        if not install_bat_path:
            logger.warning(f"Could not find install.bat in any of these locations: {[str(p) for p in possible_paths]}")
            return
        
        # Read the current content
        try:
            content = install_bat_path.read_text(encoding='utf-8')
        except Exception as e:
            logger.error(f"Failed to read install.bat: {e}")
            return
        
        # Check if the content needs updating
        placeholder = "{{VAPIORC_HOST_IP}}"
        needs_update = False
        
        if placeholder in content:
            logger.info(f"Found placeholder {placeholder}, replacing with {cls.HOST_IP}")
            updated_content = content.replace(placeholder, cls.HOST_IP)
            needs_update = True
        elif cls.HOST_IP not in content:
            # Check if there's an old IP that needs to be replaced
            # Look for the pattern WEBHOOK_HOST = "x.x.x.x"
            import re
            ip_pattern = r'WEBHOOK_HOST = "[^"]*"'
            if re.search(ip_pattern, content):
                logger.info(f"Found existing IP pattern, replacing with {cls.HOST_IP}")
                updated_content = re.sub(ip_pattern, f'WEBHOOK_HOST = "{cls.HOST_IP}"', content)
                needs_update = True
            else:
                logger.warning(f"install.bat may not be configured with correct host IP. Expected: {cls.HOST_IP}")
                return
        else:
            logger.info(f"install.bat already contains correct IP: {cls.HOST_IP}")
            return
        
        if needs_update:
            try:
                # Write the updated content back
                install_bat_path.write_text(updated_content, encoding='utf-8')
                logger.info(f"Successfully updated install.bat with host IP: {cls.HOST_IP}")
            except Exception as e:
                logger.error(f"Failed to write updated install.bat: {e}")

settings = Settings()