"""Application settings (lab only, no secrets)."""

from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "GHOSTPATH X"
    version: str = "0.4.0"
    host: str = "127.0.0.1"
    port: int = 8000
    lab_name: str = "Juice Shop Training Lab"
    environment: str = "lab"
    # Owner lock: SHA-256 hash of the owner's 6-digit PIN. The PIN
    # itself is never stored. This is a showcase lock, not real auth.
    owner_pin_hash: str = "6bd14de4a09ec57ddae07b2376188c79bfba894e73b244769872da43521dc4c4"


settings = Settings()
