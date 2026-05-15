from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Auth
    secret_key: SecretStr
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    # DB
    database_url: str

    # Redis
    redis_url: str

    # CORS — comma-separated list of allowed origins. Defaults cover local dev.
    cors_origins: str = (
        "http://localhost:3000,http://localhost:5173,"
        "http://127.0.0.1:3000,http://127.0.0.1:5173"
    )



    # Google OAuth (web)
    google_web_client_id: str = ""
    google_web_client_secret: SecretStr = SecretStr("")

    # Halyk ePay (KZ payments, test env by default)
    halyk_client_id: str = ""
    halyk_client_secret: SecretStr = SecretStr("")
    halyk_shop_id: str = ""
    halyk_terminal_id: str = ""
    halyk_oauth_url: str = "https://test-epay-oauth.epayment.kz/oauth2/token"
    halyk_api_url: str = "https://test-epay-api.epayment.kz"
    # Where Halyk POSTs the result after the user finishes payment (server endpoint).
    halyk_postlink_url: str = "http://localhost:8000/payments/halyk/postlink"
    # Where the user gets redirected after payment (frontend pages).
    # We append ?payment_id=... so the success page can poll for status.
    halyk_back_link: str = "http://localhost:5173/payment/success"
    halyk_failure_back_link: str = "http://localhost:5173/payment/failure"


settings = Settings()