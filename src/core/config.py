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
    CONTAINER_ASSETS_DIR: str = "/app/assets"  # Mounted via docker-compose
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
        
        # Simple path - assets are mounted to /app/assets via docker-compose
        install_bat_path = Path(cls.CONTAINER_ASSETS_DIR) / "install.bat"
        
        logger.info(f"Checking for install.bat at: {install_bat_path}")
        if not install_bat_path.exists():
            logger.error(f"Could not find install.bat at {install_bat_path}")
            logger.error("Make sure assets folder is properly mounted in docker-compose.yml")
            return
        
        # Read the current content
        try:
            content = install_bat_path.read_text(encoding='utf-8')
            logger.info(f"Successfully read install.bat content ({len(content)} characters)")
        except Exception as e:
            logger.error(f"Failed to read install.bat: {e}")
            return
        
        # Check if the content needs updating
        placeholder = "{{VAPIORC_HOST_IP}}"
        needs_update = False
        updated_content = content
        
        if placeholder in content:
            logger.info(f"Found placeholder {placeholder}, replacing with {cls.HOST_IP}")
            updated_content = content.replace(placeholder, cls.HOST_IP)
            needs_update = True
        else:
            # Check if there's an old IP that needs to be replaced
            # Look for the pattern WEBHOOK_HOST = "x.x.x.x"
            import re
            ip_pattern = r'WEBHOOK_HOST = "[^"]*"'
            match = re.search(ip_pattern, content)
            if match:
                current_ip = match.group(0)
                expected_line = f'WEBHOOK_HOST = "{cls.HOST_IP}"'
                if current_ip != expected_line:
                    logger.info(f"Found existing IP pattern '{current_ip}', replacing with '{expected_line}'")
                    updated_content = re.sub(ip_pattern, expected_line, content)
                    needs_update = True
                else:
                    logger.info(f"install.bat already contains correct IP: {cls.HOST_IP}")
                    return
            else:
                logger.warning(f"install.bat does not contain placeholder or IP pattern. Content preview: {content[:200]}...")
                return
        
        if needs_update:
            try:
                # Write the updated content back
                install_bat_path.write_text(updated_content, encoding='utf-8')
                logger.info(f"Successfully updated install.bat with host IP: {cls.HOST_IP}")
                
                # Verify the change was made
                verify_content = install_bat_path.read_text(encoding='utf-8')
                if cls.HOST_IP in verify_content and placeholder not in verify_content:
                    logger.info("Verified that install.bat was updated correctly")
                else:
                    logger.error("Failed to verify install.bat update")
            except Exception as e:
                logger.error(f"Failed to write updated install.bat: {e}")

settings = Settings()