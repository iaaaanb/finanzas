from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    gmail_credentials_path: str = "/app/credentials/gmail_credentials.json"
    gmail_token_path: str = "/app/credentials/gmail_token.json"
    # Modo demo: reemplaza Gmail por una casilla en memoria (app.demo) para
    # que la app se pueda levantar y probar sin credenciales de Google.
    demo_mode: bool = False

    model_config = {"env_file": ".env"}


settings = Settings()
