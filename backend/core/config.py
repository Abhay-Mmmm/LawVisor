"""
LawVisor Configuration Module
=============================
Centralized configuration management using Pydantic Settings.
All environment variables are validated and typed.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Uses Pydantic v2 settings management for type safety and validation.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # === API Keys (OpenAI & Pinecone) ===
    openai_api_key: str = Field(default="", description="OpenAI API key")
    
    # === LLM Configuration ===
    llm_model: str = Field(
        default="gpt-4o-mini",
        description="OpenAI model identifier"
    )
    
    # === Vector Database (Pinecone) ===
    pinecone_api_key: str = Field(default="", description="Pinecone API key")
    pinecone_environment: str = Field(default="us-east-1", description="Pinecone environment")
    pinecone_index_name: str = Field(default="lawvisor-regulations", description="Pinecone index name")
    
    # === Cache Configuration (local disk) ===
    cache_ttl_seconds: int = Field(default=3600, description="Cache TTL in seconds")
    
    # === OCR Configuration ===
    tesseract_path: str = Field(
        default="/usr/bin/tesseract",
        description="Path to Tesseract OCR binary"
    )
    ocr_confidence_threshold: float = Field(
        default=0.7,
        description="Minimum OCR confidence score (0-1)"
    )
    
    # === Document Storage ===
    upload_dir: Path = Field(default=Path("./uploads"), description="Upload directory")
    max_file_size_mb: int = Field(default=50, description="Maximum file size in MB")
    
    # === Server Configuration ===
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    debug: bool = Field(default=False, description="Debug mode")
    
    # === Logging ===
    log_level: str = Field(default="INFO", description="Logging level")
    
    @field_validator("upload_dir", mode="before")
    @classmethod
    def ensure_upload_dir(cls, v: str | Path) -> Path:
        """Ensure upload directory exists."""
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def max_file_size_bytes(self) -> int:
        """Get max file size in bytes."""
        return self.max_file_size_mb * 1024 * 1024
    
    def validate_llm_config(self) -> None:
        """Validate that the required API keys are set."""
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required")
        if not self.pinecone_api_key:
            raise ValueError("PINECONE_API_KEY is required")


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses lru_cache to ensure settings are loaded only once.
    """
    settings = Settings()
    return settings


# Clause type definitions for the legal domain
CLAUSE_TYPES = [
    "data_protection",
    "liability",
    "termination",
    "intellectual_property",
    "jurisdiction",
    "confidentiality",
    "indemnification",
    "force_majeure",
    "payment_terms",
    "warranties",
    "dispute_resolution",
    "amendment",
    "assignment",
    "governing_law",
    "severability",
    "notices",
    "entire_agreement",
    "counterparts",
    "unknown"
]

# Risk level definitions
RISK_LEVELS = {
    "critical": {"score_range": (80, 100), "color": "#FF0000", "label": "Critical Risk"},
    "high": {"score_range": (60, 79), "color": "#FF6B00", "label": "High Risk"},
    "medium": {"score_range": (40, 59), "color": "#FFB800", "label": "Medium Risk"},
    "low": {"score_range": (20, 39), "color": "#00C853", "label": "Low Risk"},
    "minimal": {"score_range": (0, 19), "color": "#00E676", "label": "Minimal Risk"}
}

# Regulatory sources
REGULATORY_SOURCES = {
    "gdpr": {
        "name": "General Data Protection Regulation",
        "base_url": "https://gdpr-info.eu",
        "articles_endpoint": "/art-{article_num}-gdpr/"
    },
    "sec": {
        "name": "SEC Regulations",
        "base_url": "https://www.sec.gov",
        "regulations_endpoint": "/regulations"
    }
}
