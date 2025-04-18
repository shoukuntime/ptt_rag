from pydantic_settings import BaseSettings, SettingsConfigDict
from ptt_rag import settings as ptt_rag_settings

BASE_DIR = ptt_rag_settings.BASE_DIR


class Settings(BaseSettings):
    pinecone_api_key: str = None
    openai_api_key: str = None
    pinecone_index_name: str = None
    mysql_database: str = None
    mysql_user: str = None
    mysql_password: str = None
    mysql_root_password: str = None

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env")


settings = Settings()