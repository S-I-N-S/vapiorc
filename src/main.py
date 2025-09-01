from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import asyncio

from api import health, vms, webhook
from core.db import init_db
from core.config import settings
from services.vm_manager import VMManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

vm_manager = VMManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database
    init_db()
    
    # Ensure directories exist
    settings.ensure_directories()
    
    # Ensure install script is configured with correct host IP
    logger.info(f"Configuring install.bat with host IP: {settings.HOST_IP}")
    settings.ensure_install_script_configured()
    
    # Start hot spare management in background
    asyncio.create_task(vm_manager.ensure_hot_spares())
    
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Simple containerized Windows VM orchestrator with hot spares",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(vms.router, prefix="/api/vms", tags=["vms"])
app.include_router(webhook.router, prefix="/webhook", tags=["webhook"])

@app.get("/", summary="API Root")
def root():
    return {
        "message": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            "health": "/health",
            "vms": "/api/vms",
            "golden_images": "/api/vms/golden-images",
            "assign_vm": "/api/vms/assign",
            "instances": "/api/vms/instances",
            "webhook": "/webhook"
        }
    }
