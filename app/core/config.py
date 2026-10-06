from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MONGO_URL: str
    database_name: str
    jwt_secret_key: str

    class Config:
        env_file = ".env"


settings = Settings()

JWT_SECRET_KEY = settings.jwt_secret_key
JWT_ALGORITHM = "HS256"
JWT_ISSUER = "hospital-management-api"
JWT_AUDIENCE = "hospital-management-client"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 15
