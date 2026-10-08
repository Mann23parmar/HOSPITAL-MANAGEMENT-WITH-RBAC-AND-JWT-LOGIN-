from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    MONGO_URL: str
    database_name: str
    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: str
    jwt_issuer: str
    jwt_audience: str
    jwt_access_token_expire_minutes: int = Field(gt=0)
    admin_invitation_expire_minutes: int = Field(default=60, gt=0)
    admin_setup_url: str = "http://localhost:8000/setup/admin/invitation"
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret_key(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("JWT_SECRET_KEY must not be blank")
        return value

    @field_validator("jwt_algorithm")
    @classmethod
    def validate_jwt_algorithm(cls, value: str) -> str:
        if value != "HS256":
            raise ValueError("JWT_ALGORITHM must be exactly 'HS256'")
        return value


settings = Settings()

JWT_SECRET_KEY = settings.jwt_secret_key
JWT_ALGORITHM = settings.jwt_algorithm
JWT_ISSUER = settings.jwt_issuer
JWT_AUDIENCE = settings.jwt_audience
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = settings.jwt_access_token_expire_minutes
