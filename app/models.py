from sqlalchemy import Column, Integer, String, Float, JSON, DateTime, Boolean
from sqlalchemy.sql import func
from .db import Base

class ModelVersion(Base):
    __tablename__ = "model_versions"
    id = Column(Integer, primary_key=True, index=True)
    version = Column(String, unique=True, index=True)
    metrics = Column(JSON, nullable=False)
    promoted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ConfigKV(Base):
    __tablename__ = "config_kv"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)
    value = Column(JSON, nullable=False)

class EvolutionLog(Base):
    __tablename__ = "evolution_log"
    id = Column(Integer, primary_key=True, index=True)
    message = Column(String, nullable=False)
    data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
