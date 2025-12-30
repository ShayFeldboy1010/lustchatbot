from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional
import os


# Get the project root directory (parent of backend)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Settings(BaseSettings):
    # API Keys
    google_api_key: str
    openai_api_key: str = ""  # Optional - not needed since we removed vector search

    # MongoDB (kept for potential future use, but not required for knowledge base)
    mongodb_uri: str = ""
    mongodb_database: str = "ecommerce"
    mongodb_collection: str = "data-for-ai"
    mongodb_vector_index: str = "rag_vector_index"

    # Google Sheets
    google_sheets_credentials_path: str = "./credentials.json"
    google_sheets_credentials_json: str = ""  # JSON string for cloud deployment
    google_sheets_spreadsheet_id: str
    google_sheets_sheet_name: str = "Lust leads"

    # WhatsApp Business API
    whatsapp_access_token: str
    whatsapp_phone_number_id: str
    whatsapp_business_account_id: str
    whatsapp_verify_token: str = "lustbot_whatsapp_verify_2024"
    whatsapp_human_support_number: str = "972526001060"

    # Application
    secret_key: str
    debug: bool = False

    model_config = SettingsConfigDict(
        env_file=os.path.join(PROJECT_ROOT, ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
