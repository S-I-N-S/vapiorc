from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import func
import redis
from typing import Generator
import logging

from .config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
redis_client = redis.from_url(settings.REDIS_URL)

class GoldenImage(Base):
    __tablename__ = "golden_images"
    
    id = Column(String, primary_key=True)
    vm_type = Column(String, nullable=False, default="11")
    status = Column(String, nullable=False)  # creating, ready, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class VMInstance(Base):
    __tablename__ = "vm_instances"
    
    id = Column(String, primary_key=True)
    container_id = Column(String, unique=True, nullable=True)
    vm_type = Column(String, nullable=False, default="11")
    status = Column(String, nullable=False)  # starting, ready, busy, stopping, stopped
    port = Column(Integer, nullable=True)
    is_hot_spare = Column(Boolean, default=False)
    assigned_to = Column(String, nullable=True)  # For tracking assignments
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_redis() -> redis.Redis:
    return redis_client

def init_db():
    """Initialize database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise