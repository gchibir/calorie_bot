import os
import logging
import requests
from telegram import Update
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters, CallbackContext
)
from fastapi import FastAPI, Request
import uvicorn
import threading

# Логирование
logging.basicConfig(level=logging.INFO)

# Получаем токены из переменных окружения
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
SPOONACULAR_KEY = os.environ.get("SPOONACULAR_KEY")

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "📸 Отправь фото еды или напиши название блюда — я подскажу калории!\n"
        "Примеры: «омлет», «банан», «пицца маргарита»"
    )

def handle_text(update: Update, context: CallbackContext):
    query = update.message.text.strip()
    update.message.reply_text("🔍 Ищу информацию о калориях...")

    # Запрос к Spoonacular API
    url = "https://api.spoonacular.com/food/products/search"
    params = {
        "query": query,
        "number": 1,
        "apiKey": SPOONACULAR_KEY
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if data.get("products"):
            product = data["products"][0]
            title = product.get("title", query)
            calories = product.get("calories", "неизвестно")
            update.message.reply_text(
                f"✅ {title}\n🔥 Калории: ~{calories} ккал на 100г"
            )
        else:
            update.message.reply_text(
                "❌ Не нашёл информацию об этом блюде. Попробуй другое название."
            )
    except Exception as e:
        update.message.reply_text(f"⚠️ Ошибка: {str(e)}")

def handle_photo(update: Update, context: CallbackContext):
    update.message.reply_text(
        "📸 Фото получено!\n"
        "⚠️ В бесплатной версии я пока распознаю только текст. "
        "Отправь название блюда словами — например, «гречка с курицей»."
    )

# Создаём updater
updater = Updater(token=TELEGRAM_TOKEN, use_context=True)

# Добавляем обработчики
updater.dispatcher.add_handler(CommandHandler("start", start))
updater.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
updater.dispatcher.add_handler(MessageHandler(Filters.photo, handle_photo))

# FastAPI приложение для обработки Webhook
app = FastAPI()

@app.post("/")
async def handle_telegram_webhook(request: Request):
    """Обрабатываем входящие обновления от Telegram"""
    try:
        update_data = await request.json()
        # Добавляем обновление в очередь updater
        updater.update_queue.put_nowait(Update.de_json(update_data))
        return {"status": "ok"}
    except Exception as e:
        print(f"Ошибка при обработке webhook: {e}")
        return {"status": "error"}

def run_updater():
    updater.start_polling()

if __name__ == "__main__":
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN не установлен!")
    if not SPOONACULAR_KEY:
        raise ValueError("SPOONACULAR_KEY не установлен!")

    # Запускаем updater в отдельном потоке
    thread = threading.Thread(target=run_updater, daemon=True)
    thread.start()

    # Запускаем FastAPI сервер
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=False)
