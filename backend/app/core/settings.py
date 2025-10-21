from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import json

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(..., env="DATABASE_URL")
    openai_api_key: str | None = Field(default=None, env="OPENAI_API_KEY")
    embedding_model: str = Field(default="text-embedding-3-small", env="EMBEDDING_MODEL")
    chat_model: str = Field(default="gpt-4o-mini", env="CHAT_MODEL")
    # Raw env value; parsed via `allow_origins` property to avoid JSON pre-parse by pydantic-settings
    allow_origins_raw: str | None = Field(default=None, env="ALLOW_ORIGINS")
    upload_dir: Path = Field(default=Path("uploads"), env="UPLOAD_DIR")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    @property
    def allow_origins(self) -> list[str]:
        raw = self.allow_origins_raw
        if raw is None:
            return []
        s = str(raw).strip()
        if not s:
            return []
        # Try JSON list first
        if s.startswith("[") and s.endswith("]"):
            try:
                data = json.loads(s)
                if isinstance(data, list):
                    return [str(v).strip() for v in data if str(v).strip()]
            except Exception:
                # fall back to CSV parsing
                pass
        return [item.strip() for item in s.split(",") if item.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    


 


