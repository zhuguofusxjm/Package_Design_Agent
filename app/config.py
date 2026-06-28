import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    data_dir: str = os.path.join(os.path.dirname(__file__), "data")
    skills_dir: str = os.path.join(os.path.dirname(__file__), "skills")
    static_dir: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")

settings = Settings()
