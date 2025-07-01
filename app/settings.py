from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os


class Settings(BaseSettings):
    # OpenAI
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    openai_model: str = "gpt-4o-mini"
    
    # Pinecone
    pinecone_api_key: Optional[str] = Field(None, env="PINECONE_API_KEY")
    pinecone_env: str = Field("us-east-1-aws", env="PINECONE_ENVIRONMENT")
    pinecone_index_name: str = Field("lust-products", env="PINECONE_INDEX_NAME")
    
    # External APIs
    firecrawl_api_key: Optional[str] = Field(None, env="FIRECRAWL_API_KEY")
    
    # Google Services
    google_sheets_api_key: Optional[str] = Field(None, env="GOOGLE_SHEETS_API_KEY")
    google_sheets_credentials_path: str = Field("creds/sheets.json", env="GOOGLE_APPLICATION_CREDENTIALS")
    google_sheets_id: str = Field(..., env="GOOGLE_SHEETS_SPREADSHEET_ID")
    sheet_id: Optional[str] = Field(None, env="GOOGLE_SHEET_ID")  # Legacy support
    
    # Agent Settings
    agent_model: str = "gpt-4o-mini"
    agent_temperature: float = 0.7
    
    # App Settings
    debug: bool = Field(False, env="DEBUG")
    
    # Server Settings (for Render deployment)
    host: str = Field("0.0.0.0", env="HOST")
    port: int = Field(8000, env="PORT")
    
    # CORS
    cors_origins: list = ["*"]  # In production: ["https://mylustshop.com"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Allow extra fields in .env without erroring


# Create settings instance
settings = Settings()

# For backward compatibility
OPENAI_API_KEY = settings.openai_api_key
PINECONE_API_KEY = settings.pinecone_api_key
FIRECRAWL_API_KEY = settings.firecrawl_api_key
AGENT_MODEL = settings.agent_model
AGENT_TEMPERATURE = settings.agent_temperature
