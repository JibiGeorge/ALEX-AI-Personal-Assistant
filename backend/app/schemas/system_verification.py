from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class HardwareVerification(BaseModel):
    model_config = ConfigDict(extra="ignore")

    os_name: str
    os_version: str
    architecture: str
    cpu_model: str
    cpu_physical_cores: int = Field(ge=1)
    cpu_logical_cores: int = Field(ge=1)
    cpu_percent: float = Field(ge=0, le=100)
    ram_total_gb: float = Field(ge=0)
    ram_available_gb: float = Field(ge=0)
    ram_percent: float = Field(ge=0, le=100)
    gpu_available: bool
    gpu_model: Optional[str] = None
    gpu_percent: Optional[float] = None
    gpu_temperature_c: Optional[float] = None
    disk_total_gb: float = Field(ge=0)
    disk_free_gb: float = Field(ge=0)
    disk_percent: float = Field(ge=0, le=100)
    network_interfaces_count: int = Field(ge=0)
    internet_connected: bool
    uptime_seconds: int = Field(ge=0)
    process_count: int = Field(ge=0)


class ApplicationVerification(BaseModel):
    model_config = ConfigDict(extra="ignore")

    app_name: str
    app_version: str
    execution_environment: str
    python_version: str
    python_executable: str
    fastapi_version: str
    dependencies_installed: list[str]
    missing_dependencies: list[str]
    workspace_path: str
    workspace_readable: bool
    workspace_writable: bool
    config_files_valid: bool
    secrets_sanitized: bool


class BackendDatabaseVerification(BaseModel):
    model_config = ConfigDict(extra="ignore")

    backend_online: bool
    loopback_endpoint: str
    database_type: str
    memory_store_accessible: bool
    memory_entries_count: int
    reminder_store_accessible: bool
    active_reminders_count: int
    scheduler_active: bool
    background_workers_active: bool


class AiEngineVerification(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ollama_installed: bool
    ollama_running: bool
    ollama_version: Optional[str] = None
    ollama_models: list[str]
    ollama_default_model: Optional[str] = None
    lmstudio_running: bool
    lmstudio_models: list[str]
    cloud_provider: str
    cloud_credentials_configured: bool
    cloud_connectivity_verified: bool
    cloud_models_available: list[str]
    grounded_search_available: bool


class FullSystemVerificationReport(BaseModel):
    model_config = ConfigDict(extra="ignore")

    timestamp: str
    status: str
    overall_score: int = Field(ge=0, le=100)
    hardware: HardwareVerification
    application: ApplicationVerification
    backend_database: BackendDatabaseVerification
    ai_engines: AiEngineVerification

