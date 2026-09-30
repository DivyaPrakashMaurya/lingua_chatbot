from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

ROOT = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    app_name: str = 'Lingua'
    chat_mode: Literal['demo', 'local', 'huggingface'] = 'demo'
    intent_mode: Literal['demo', 'transformer'] = 'demo'
    hf_token: str = ''
    hf_chat_model: str = 'Qwen/Qwen2.5-7B-Instruct'
    local_chat_model: str = 'Qwen/Qwen2.5-0.5B-Instruct'
    intent_model: str = 'MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli'
    database_path: str = 'data/lingua.db'
    context_messages: int = Field(default=12, ge=2, le=40)
    max_new_tokens: int = Field(default=384, ge=32, le=2048)
    model_config = SettingsConfigDict(env_file=ROOT / '.env', extra='ignore')

settings = Settings()
