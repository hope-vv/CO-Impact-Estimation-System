import os
from dotenv import load_dotenv

load_dotenv()

def get_env_variable(name: str, required: bool = True) -> str:
    value = os.getenv(name)
    if required and not value:
        raise ValueError(f"Required environment variable '{name}' is not set.")
    return value


class Config:
    DATABASE_URL: str = get_env_variable("DATABASE_URL", required=False)
    DB_HOST: str = get_env_variable("DB_HOST", required=not DATABASE_URL)
    DB_PORT: int = int(get_env_variable("DB_PORT", required=not DATABASE_URL) or 5432)
    DB_USER: str = get_env_variable("DB_USER", required=not DATABASE_URL)
    DB_PASSWORD: str = get_env_variable("DB_PASSWORD", required=not DATABASE_URL)
    DB_NAME: str = get_env_variable("DB_NAME", required=not DATABASE_URL)
    DATA_BATCH_SIZE: int = int(get_env_variable("DATA_BATCH_SIZE"))

    def database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    
def get_config() -> Config:
    return Config()