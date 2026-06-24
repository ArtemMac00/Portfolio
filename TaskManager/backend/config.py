import os
from dotenv import load_dotenv

load_dotenv()

AGNES_API_KEY = os.getenv("AGNES_API_KEY")
MODEL = os.getenv("MODEL", "agnes-2.0-flash")
BASE_URL = "https://apihub.agnes-ai.com/v1"

if not AGNES_API_KEY:
    raise ValueError("AGNES_API_KEY не найден в .env файле!")

AI_SYSTEM_PROMPT = """Ты — помощник по управлению задачами.
Определи приоритет задачи (High/Medium/Low) по описанию.
Верни только одно слово: High, Medium или Low.
Если задача срочная, связана с деньгами или дедлайном — ставь High.
Если обычная рабочая задача — Medium.
Если неважная или личная — Low."""
