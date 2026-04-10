from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    gmail_credentials_path: str = "/app/credentials/gmail_credentials.json"
    gmail_token_path: str = "/app/credentials/gmail_token.json"

    model_config = {"env_file": ".env"}


settings = Settings()
