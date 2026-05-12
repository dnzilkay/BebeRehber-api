from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "BebeRehber API"
    APP_ENV: str = "development"

    DATABASE_URL: str = "postgresql+psycopg://beberehber:beberehber@db:5432/beberehber"

    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    BACKEND_CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # MinIO object storage
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "beberehber"
    MINIO_SECRET_KEY: str = "beberehber123"
    MINIO_BUCKET: str = "beberehber-media"
    MINIO_PUBLIC_URL: str = "http://localhost:9000"
    MINIO_USE_SSL: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.BACKEND_CORS_ORIGINS.split(",")
            if origin.strip()
        ]


settings = Settings()
