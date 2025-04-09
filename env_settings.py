from pydantic_settings import BaseSettings, SettingsConfigDict
from ptt_rag import settings as ptt_rag_settings

BASE_DIR = ptt_rag_settings.BASE_DIR


class Settings(BaseSettings):
    pinecone_api_key: str = None
    openai_api_key: str = None
    pinecone_index_name: str = 'ptt'

    model_config = SettingsConfigDict(env_file=f'{BASE_DIR}\.env')


settings = Settings()

