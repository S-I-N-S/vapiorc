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
    
    @classmethod
    def ensure_directories(cls):
        """Ensure all required directories exist"""
        for path in [cls.DATA_PATH, cls.GOLDEN_IMAGES_PATH, cls.INSTANCES_PATH]:
            Path(path).mkdir(parents=True, exist_ok=True)

settings = Settings()