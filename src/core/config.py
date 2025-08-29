import os
from pathlib import Path
from typing import Optional

class Settings:
    """Simple configuration management for vapiorc"""
    
    PROJECT_NAME: str = "vapiorc - VM Orchestrator"
    VERSION: str = "0.1.0"
    
    # Base directory (where vapiorc is installed)
    BASE_DIR: str = str(Path(__file__).resolve().parent.parent)
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/vapiorcdb")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    
    # Storage paths
    STORAGE_PATH: str = os.getenv("VAPIORC_STORAGE_PATH", "/tmp/vapiorc")
    DATA_PATH: str = os.path.join(STORAGE_PATH, "data")
    GOLDEN_IMAGES_PATH: str = os.path.join(DATA_PATH, "golden_images")
    INSTANCES_PATH: str = os.path.join(DATA_PATH, "instances")
    
    # Docker settings  
    DOCKER_NETWORK: str = os.getenv("VAPIORC_NETWORK", "vapiorc_vapiorc_network")
    
    # Port management
    PORT_RANGE_START: int = int(os.getenv("VAPIORC_PORT_START", "8000"))
    PORT_RANGE_END: int = int(os.getenv("VAPIORC_PORT_END", "9000"))
    
    # Hot spare settings
    HOT_SPARE_COUNT: int = int(os.getenv("VAPIORC_HOT_SPARES", "2"))
    
    # VM Configuration
    VM_TYPE: str = "11"  # Fixed to Windows 11
    
    # Host networking
    HOST_IP: str = os.getenv("VAPIORC_HOST_IP", "192.168.1.100")
    
    @classmethod
    def ensure_directories(cls):
        """Ensure all required directories exist"""
        for path in [cls.DATA_PATH, cls.GOLDEN_IMAGES_PATH, cls.INSTANCES_PATH]:
            Path(path).mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def ensure_install_script_configured(cls):
        """Ensure install.bat has the correct host IP configured"""
        install_bat_path = Path(cls.BASE_DIR) / "assets" / "install.bat"
        
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