"""
Configuration settings for the application
"""
from pydantic_settings import BaseSettings
from typing import List, Optional
import os
from pathlib import Path


class Settings(BaseSettings):
    """Application settings"""
    
    # App
    APP_NAME: str = "Road Safety Intervention Analysis System"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    SECRET_KEY: str
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    
    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40
    
    # Redis
    REDIS_URL: str
    REDIS_CACHE_TTL: int = 86400
    
    # AI/ML
    TRANSFORMER_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    NER_MODEL: str = "en_core_web_lg"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4"
    
    # Vector Database
    CHROMA_PERSIST_DIRECTORY: str = "./data/chromadb"
    VECTOR_COLLECTION_NAME: str = "irc_standards"
    
    # Government Data Sources
    CPWD_SOR_API_URL: str = "https://cpwd.gov.in/api/sor"
    CPWD_AOR_API_URL: str = "https://cpwd.gov.in/api/aor"
    GEM_API_URL: str = "https://gem.gov.in/api/v1"
    GEM_API_KEY: Optional[str] = None
    
    # Document Processing
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: str = "pdf,docx,txt,png,jpg,jpeg"
    TESSERACT_PATH: str = "/usr/bin/tesseract"
    TEMP_UPLOAD_DIR: str = "./data/uploads"
    PROCESSED_DIR: str = "./data/processed"
    
    # Report Generation
    REPORT_OUTPUT_DIR: str = "./data/reports"
    REPORT_TEMPLATE_DIR: str = "./templates/reports"
    LOGO_PATH: str = "./static/assets/emblem.svg"
    
    # Security
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 1440
    BCRYPT_ROUNDS: int = 12
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 30
    RATE_LIMIT_PER_HOUR: int = 500
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/app.log"
    
    # Monitoring
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    
    @property
    def allowed_extensions_list(self) -> List[str]:
        """Get list of allowed file extensions"""
        return [ext.strip() for ext in self.ALLOWED_EXTENSIONS.split(",")]
    
    def ensure_directories(self):
        """Ensure all required directories exist"""
        dirs = [
            self.TEMP_UPLOAD_DIR,
            self.PROCESSED_DIR,
            self.REPORT_OUTPUT_DIR,
            self.CHROMA_PERSIST_DIRECTORY,
            Path(self.LOG_FILE).parent,
        ]
        for dir_path in dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
settings.ensure_directories()
