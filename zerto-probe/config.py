from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # ZVMA de origen (site de producción / "Remote" en la UI)
    origin_zvma_host: str
    origin_zvma_username: str
    origin_zvma_password: str
    origin_zvma_label: str = "HDM Production"

    # ZVMA de destino (site de recuperación / "Local" en la UI)
    destination_zvma_host: str
    destination_zvma_username: str
    destination_zvma_password: str
    destination_zvma_label: str = "HDM DR"

    keycloak_client_id: str = "zerto-client"
    verify_ssl: bool = False
    cache_ttl_seconds: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()
