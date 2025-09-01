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
        install_bat_path = Path(cls.HOST_ASSETS_PATH) / "install.bat"
        
        if not install_bat_path.exists():
            return
        
        # Read the current content
        content = install_bat_path.read_text(encoding='utf-8')
        
        # Check if the content needs updating
        placeholder = "{{VAPIORC_HOST_IP}}"
        if placeholder in content:
            # Replace the placeholder with the actual host IP
            updated_content = content.replace(placeholder, cls.HOST_IP)
            
            # Write the updated content back
            install_bat_path.write_text(updated_content, encoding='utf-8')
            
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Updated install.bat with host IP: {cls.HOST_IP}")
        elif cls.HOST_IP not in content:
            # Log a warning if the host IP isn't found and placeholder isn't there either
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"install.bat may not be configured with correct host IP. Expected: {cls.HOST_IP}")

settings = Settings()