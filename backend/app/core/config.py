import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # API Keys
    API_KEY: str = os.getenv("API_KEY", "")
    
    # Supabase Database
    SUPABASE_HOST: str = os.getenv("SUPABASE_HOST", "db.fzrbnsljevwhexjnfqtz.supabase.co")
    SUPABASE_PORT: int = int(os.getenv("SUPABASE_PORT", "5432"))
    SUPABASE_DATABASE: str = os.getenv("SUPABASE_DATABASE", "postgres")
    SUPABASE_USER: str = os.getenv("SUPABASE_USER", "postgres")
    SUPABASE_PASSWORD: str = os.getenv("SUPABASE_PASSWORD", "")
    
    # SQLite Database
    SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", "database.db")
    
    # FastAPI
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8001"))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    
    @property
    def supabase_url(self) -> str:
        return f"postgresql://{self.SUPABASE_USER}:{self.SUPABASE_PASSWORD}@{self.SUPABASE_HOST}:{self.SUPABASE_PORT}/{self.SUPABASE_DATABASE}"

settings = Settings()