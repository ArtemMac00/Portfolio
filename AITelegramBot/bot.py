import asyncio
import logging
import time
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)
import requests
import json

from config import (
    TELEGRAM_TOKEN,
    AGNES_API_KEY,
    MODEL,
    BASE_URL,
    MAX_HISTORY_LENGTH,
    MAX_TOKENS,
    TEMPERATURE,
    SYSTEM_PROMPT
)

# НАСТРОЙКА ЛОГИРОВАНИЯ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ХРАНИЛИЩЕ
user_histories = {}  # {user_id: [{"role": "...", "content": "..."}]}
user_stats = {}      # {user_id: {"messages": 0, "first_seen": timestamp}}

# КНОПКИ
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("🔄 Очистить историю", callback_data="reset")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ===== ОБРАБОТЧИКИ КОМАНД =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    username = update.effective_user.username or "Без имени"
    
    # Инициализируем статистику
    if user_id not in user_stats:
        user_stats[user_id] = {
            "messages": 0,
            "first_seen": datetime.now(),
            "username": username
        }
    
    # Приветствие с кнопками
    welcome_text = (
        "👋 Привет! Я **ИИ-помощник на базе Agnes AI**.\n\n"
        "📌 Я эксперт по Python и программированию.\n"
        "Задавай вопросы по коду, алгоритмам или просто болтай.\n\n"
        f"🆓 Модель: `{MODEL}`\n"
        "📊 Лимит: 20 запросов/мин\n\n"
        "**Команды:**\n"
        "/reset — очистить историю\n"
        "/stats — моя статистика\n"
        "/help — помощь"
    )
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )
    
    logger.info(f"Новый пользователь: {username} (ID: {user_id})")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    user_histories[user_id] = []
    await update.message.reply_text(
        "✅ История диалога очищена!",
        reply_markup=get_main_keyboard()
    )
    logger.info(f"Пользователь {user_id} очистил историю")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    stats = user_stats.get(user_id, {})
    msg_count = stats.get("messages", 0)
    first_seen = stats.get("first_seen", datetime.now())
    
    # Считаем длину истории
    history_len = len(user_histories.get(user_id, [])) // 2  # Пар вопрос-ответ
    
    text = (
        "📊 **Твоя статистика:**\n\n"
        f"💬 Всего сообщений: `{msg_count}`\n"
        f"🔄 Пар диалога в памяти: `{history_len}`\n"
        f"📅 Впервые здесь: `{first_seen.strftime('%d.%m.%Y %H:%M')}`\n"
        f"🤖 Модель: `{MODEL}`"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🆘 **Помощь**\n\n"
        "Я — ИИ-помощник. Вот что я умею:\n\n"
        "✅ Отвечать на вопросы по Python и программированию\n"
        "✅ Писать и объяснять код\n"
        "✅ Помогать с алгоритмами и задачами\n"
        "✅ Поддерживать контекст диалога\n\n"
        "**Команды:**\n"
        "/start — главное меню\n"
        "/reset — очистить историю\n"
        "/stats — моя статистика\n"
        "/help — это сообщение\n\n"
        "**Совет:** Чем подробнее вопрос — тем точнее ответ!"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

# ОБРАБОТЧИК КНОПОК
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "reset":
        user_id = query.from_user.id
        user_histories[user_id] = []
        await query.edit_message_text("✅ История очищена!", reply_markup=get_main_keyboard())
    
    elif query.data == "help":
        help_text = (
            "🆘 **Помощь**\n\n"
            "Задавай вопросы по Python, алгоритмам или просто общайся!\n"
            "Команды: /start, /reset, /stats, /help"
        )
        await query.edit_message_text(help_text, parse_mode="Markdown", reply_markup=get_main_keyboard())

# ОСНОВНАЯ ЛОГИКА
def ask_agnes(messages):
    """Отправляет запрос к Agnes AI"""
    url = f"{BASE_URL}/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {AGNES_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
        elif response.status_code == 429:
            return "⏳ Превышен лимит запросов (20 в минуту). Подожди немного."
        else:
            error_msg = response.json().get("error", {}).get("message", "Неизвестная ошибка")
            return f"❌ Ошибка API: {error_msg}"
    
    except requests.exceptions.Timeout:
        return "⏰ Превышено время ожидания. Попробуй ещё раз."
    except requests.exceptions.ConnectionError:
        return "🌐 Нет соединения с сервером. Проверь интернет."
    except Exception as e:
        return f"❌ Непредвиденная ошибка: {str(e)}"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    user_text = update.message.text
    
    # Обновляем статистику
    if user_id not in user_stats:
        user_stats[user_id] = {
            "messages": 0,
            "first_seen": datetime.now(),
            "username": update.effective_user.username or "Без имени"
        }
    user_stats[user_id]["messages"] += 1
    
    # Показываем "печатает"
    await update.message.chat.send_action(action="typing")
    
    # Получаем или создаём историю
    history = user_histories.get(user_id, [])
    
    # Если история пустая — добавляем системный промпт
    if not history:
        history.append({"role": "system", "content": SYSTEM_PROMPT})
    
    # Добавляем сообщение пользователя
    history.append({"role": "user", "content": user_text})
    
    # Ограничиваем историю
    if len(history) > MAX_HISTORY_LENGTH * 2 + 1:  # +1 за системный
        # Оставляем системный промпт и последние MAX_HISTORY_LENGTH*2 сообщений
        history = [history[0]] + history[-(MAX_HISTORY_LENGTH * 2):]
    
    # Получаем ответ от ИИ
    reply = ask_agnes(history)
    
    # Сохраняем ответ в историю
    history.append({"role": "assistant", "content": reply})
    user_histories[user_id] = history
    
    # Отправляем ответ с кнопками
    await update.message.reply_text(
        reply,
        reply_markup=get_main_keyboard()
    )
    
    logger.info(f"Пользователь {user_id}: {user_text[:50]}... -> ответ получен")

# ОБРАБОТКА ОШИБОК
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Ошибка: {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "😅 Произошла техническая ошибка. Попробуй ещё раз."
        )

# ЗАПУСК
def main():
    print(f"🚀 Запуск бота...")
    print(f"🤖 Модель: {MODEL}")
    print(f"🔗 API: {BASE_URL}")
    print("💬 Жду сообщений...")
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("help", help_command))
    
    # Кнопки
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Текстовые сообщения
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Ошибки
    app.add_error_handler(error_handler)
    
    app.run_polling()

if __name__ == "__main__":
    main()
