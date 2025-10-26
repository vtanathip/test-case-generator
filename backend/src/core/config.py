"""Configuration management using Pydantic settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application configuration from environment variables."""
    
    # GitHub Configuration
    github_token: str = "test_token"
    github_webhook_secret: str = "test_secret"
    github_repo: str = "owner/repo"
    
    # Llama 3.2 Configuration
    llama_model: str = "llama3.2:11b"
    ollama_host: str = "http://ollama:11434"
    ollama_timeout: int = 120
    
    # ChromaDB Configuration
    chromadb_host: str = "chromadb"
    chromadb_port: int = 8000
    chromadb_collection: str = "test_cases"
    chromadb_embedding_model: str = "all-MiniLM-L6-v2"
    
    # Redis Configuration
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    redis_idempotency_ttl: int = 3600  # 1 hour
    
    # Backend Configuration
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    backend_log_level: str = "INFO"
    backend_cors_origins: str = "http://localhost:3000"
    
    # Performance Configuration
    max_concurrent_webhooks: int = 100
    webhook_timeout: int = 10
    ai_generation_timeout: int = 120
    vector_query_timeout: int = 5
    github_api_timeout: int = 30
    
    # Feature Flags
    enable_vector_context: bool = True
    enable_idempotency_cache: bool = True
    enable_metrics: bool = True
    
    # Development
    debug: bool = False
    testing: bool = False
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins string to list."""
        return [origin.strip() for origin in self.backend_cors_origins.split(",")]


# Global settings instance
settings = Settings()
