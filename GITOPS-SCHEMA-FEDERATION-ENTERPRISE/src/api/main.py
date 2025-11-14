"""
FastAPI application for multi-backend schema registry.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import List, Optional

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..core import (
    CompatibilityMode,
    MultiBackendOrchestrator,
    RegistryConfig,
    RegistryType,
    SchemaFormat,
    get_plugin_registry
)
from ..plugins.confluent import ConfluentSchemaRegistryPlugin
from ..plugins.unity_catalog import UnityCatalogPlugin


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Global orchestrator instance
orchestrator: Optional[MultiBackendOrchestrator] = None


# Pydantic models for API
class RegistryInfo(BaseModel):
    id: str
    type: str
    supported_formats: List[str]


class HealthCheckResponse(BaseModel):
    healthy: bool
    status_code: int
    message: str
    response_time_ms: float


class CompatibilityCheckRequest(BaseModel):
    subject: str
    schema_content: str
    schema_format: str
    version: Optional[int] = None


class CompatibilityCheckResponse(BaseModel):
    is_compatible: bool
    messages: List[str]
    compatibility_level: str
    errors: List[str]


class SetCompatibilityRequest(BaseModel):
    mode: str
    subject: Optional[str] = None


class BulkCheckRequest(BaseModel):
    registry_ids: List[str]
    target_mode: str
    subject_filter: Optional[str] = None


# Lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global orchestrator

    # Startup
    logger.info("Starting multi-backend schema registry API...")

    # Initialize plugin registry
    plugin_registry = get_plugin_registry()

    # Register plugins
    plugin_registry.register_plugin(RegistryType.CONFLUENT, ConfluentSchemaRegistryPlugin)
    plugin_registry.register_plugin(RegistryType.UNITY_CATALOG, UnityCatalogPlugin)

    # Initialize orchestrator
    orchestrator = MultiBackendOrchestrator(plugin_registry)

    # Load configuration
    config_path = os.getenv("REGISTRY_CONFIG", "config/registries.yaml")
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)

        # Add registries from config
        for registry_config in config_data.get("registries", []):
            if registry_config.get("enabled", True):
                try:
                    # Expand environment variables
                    for key in ["username", "password", "token"]:
                        if key in registry_config.get("auth", {}):
                            value = registry_config["auth"][key]
                            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                                env_var = value[2:-1]
                                registry_config["auth"][key] = os.getenv(env_var, "")

                    config = RegistryConfig(
                        id=registry_config["id"],
                        type=RegistryType[registry_config["type"].upper()],
                        url=registry_config["url"],
                        auth=registry_config.get("auth", {}),
                        ssl_config=registry_config.get("ssl_config", {}),
                        timeout=registry_config.get("timeout", 30),
                        max_retries=registry_config.get("max_retries", 3),
                        metadata=registry_config.get("metadata", {}),
                        enabled=registry_config.get("enabled", True)
                    )

                    orchestrator.add_registry(config)
                    logger.info(f"Added registry: {config.id}")

                except Exception as e:
                    logger.error(f"Failed to add registry {registry_config.get('id')}: {e}")

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down...")
    if orchestrator:
        orchestrator.shutdown()


# Create FastAPI app
app = FastAPI(
    title="Multi-Backend Schema Registry API",
    description="Unified API for managing schemas across multiple registry backends",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== Registry Management Endpoints =====

@app.get("/api/v1/registries", response_model=List[RegistryInfo])
async def list_registries():
    """List all configured registries."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    registries = orchestrator.list_registries()
    return [RegistryInfo(**r) for r in registries]


@app.get("/api/v1/registries/{registry_id}/health", response_model=HealthCheckResponse)
async def check_registry_health(registry_id: str):
    """Check health of a specific registry."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    registry = orchestrator.get_registry(registry_id)
    if not registry:
        raise HTTPException(status_code=404, detail=f"Registry {registry_id} not found")

    health = registry.health_check()
    return HealthCheckResponse(**health.to_dict())


@app.get("/api/v1/health/all")
async def check_all_health():
    """Check health of all registries."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    health_statuses = orchestrator.health_check_all()
    return {
        registry_id: status.to_dict()
        for registry_id, status in health_statuses.items()
    }


# ===== Schema Operations =====

@app.get("/api/v1/schemas/find")
async def find_schema_across_registries(subject: str):
    """Find a schema by subject across all registries."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    schemas = orchestrator.find_schema_across_registries(subject)

    return {
        registry_id: schema.to_dict()
        for registry_id, schema in schemas.items()
    }


@app.get("/api/v1/registries/{registry_id}/subjects")
async def list_subjects(registry_id: str, prefix: Optional[str] = None):
    """List all subjects in a registry."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    registry = orchestrator.get_registry(registry_id)
    if not registry:
        raise HTTPException(status_code=404, detail=f"Registry {registry_id} not found")

    subjects = registry.list_subjects(prefix=prefix)
    return {"subjects": subjects}


# ===== Compatibility Operations =====

@app.post("/api/v1/registries/{registry_id}/compatibility/check", response_model=CompatibilityCheckResponse)
async def check_compatibility(registry_id: str, request: CompatibilityCheckRequest):
    """Check schema compatibility."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    registry = orchestrator.get_registry(registry_id)
    if not registry:
        raise HTTPException(status_code=404, detail=f"Registry {registry_id} not found")

    try:
        schema_format = SchemaFormat[request.schema_format.upper()]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid schema format: {request.schema_format}")

    result = registry.check_compatibility(
        subject=request.subject,
        schema_content=request.schema_content,
        schema_format=schema_format,
        version=request.version
    )

    return CompatibilityCheckResponse(**result.to_dict())


@app.get("/api/v1/registries/{registry_id}/compatibility/mode")
async def get_compatibility_mode(registry_id: str, subject: Optional[str] = None):
    """Get compatibility mode (global or subject-specific)."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    registry = orchestrator.get_registry(registry_id)
    if not registry:
        raise HTTPException(status_code=404, detail=f"Registry {registry_id} not found")

    mode = registry.get_compatibility_mode(subject=subject)
    return {"mode": mode.value, "subject": subject or "global"}


@app.put("/api/v1/registries/{registry_id}/compatibility/mode")
async def set_compatibility_mode(registry_id: str, request: SetCompatibilityRequest):
    """Set compatibility mode (global or subject-specific)."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    registry = orchestrator.get_registry(registry_id)
    if not registry:
        raise HTTPException(status_code=404, detail=f"Registry {registry_id} not found")

    try:
        mode = CompatibilityMode[request.mode.upper()]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid compatibility mode: {request.mode}")

    success = registry.set_compatibility_mode(mode, subject=request.subject)

    return {
        "success": success,
        "registry_id": registry_id,
        "mode": request.mode,
        "subject": request.subject or "global"
    }


@app.get("/api/v1/compatibility/overview")
async def get_compatibility_overview():
    """Get compatibility modes from all registries."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    return orchestrator.compare_compatibility_modes()


# ===== Bulk Operations =====

@app.post("/api/v1/bulk/check-compatibility")
async def bulk_check_compatibility(request: BulkCheckRequest):
    """Check compatibility for multiple subjects across registries."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    try:
        target_mode = CompatibilityMode[request.target_mode.upper()]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid compatibility mode: {request.target_mode}")

    result = orchestrator.bulk_check_compatibility(
        registry_ids=request.registry_ids,
        target_mode=target_mode,
        subject_filter=request.subject_filter
    )

    return result.to_dict()


@app.post("/api/v1/bulk/set-compatibility")
async def bulk_set_compatibility(
    mode: str,
    registry_ids: List[str],
    subject_filter: Optional[str] = None
):
    """Set compatibility mode for multiple subjects."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    try:
        compat_mode = CompatibilityMode[mode.upper()]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid compatibility mode: {mode}")

    results = orchestrator.bulk_set_compatibility(
        registry_ids=registry_ids,
        mode=compat_mode,
        subject_filter=subject_filter
    )

    return results


# ===== Root endpoint =====

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Multi-Backend Schema Registry API",
        "version": "1.0.0",
        "documentation": "/docs",
        "health": "/api/v1/health/all"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
