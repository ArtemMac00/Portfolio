import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# Токены
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
AGNES_API_KEY = os.getenv("AGNES_API_KEY")
MODEL = os.getenv("MODEL", "agnes-2.0-flash")

# URL API
BASE_URL = "https://apihub.agnes-ai.com/v1"

# Настройки ИИ
MAX_HISTORY_LENGTH = 10  # Количество сообщений в истории
MAX_TOKENS = 500
TEMPERATURE = 0.7

# Системный промпт (роль бота)
SYSTEM_PROMPT = """Ты — опытный Python-разработчик и ИИ-ассистент. 
Отвечай кратко, понятно и по делу. 
Если пользователь просит код — приводи примеры с пояснениями.
Если вопрос не по программированию — отвечай вежливо, но старайся помочь."""

# Проверка наличия токенов
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN не найден в .env файле!")
if not AGNES_API_KEY:
    raise ValueError("AGNES_API_KEY не найден в .env файле!")
