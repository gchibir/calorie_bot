import os
import logging
import asyncio
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Логирование для отладки
logging.basicConfig(level=logging.INFO)

# Получаем токены из переменных окружения
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
SPOONACULAR_KEY = os.environ.get("SPOONACULAR_KEY")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📸 Отправь фото еды или напиши название блюда — я подскажу калории!\n"
        "Примеры: «омлет», «банан», «пицца маргарита»"
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    await update.message.reply_text("🔍 Ищу информацию о калориях...")

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
            await update.message.reply_text(
                f"✅ {title}\n🔥 Калории: ~{calories} ккал на 100г"
            )
        else:
            await update.message.reply_text(
                "❌ Не нашёл информацию об этом блюде. Попробуй другое название."
            )
    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка: {str(e)}")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📸 Фото получено!\n"
        "⚠️ В бесплатной версии я пока распознаю только текст. "
        "Отправь название блюда словами — например, «гречка с курицей»."
    )

def main():
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN не установлен!")
    if not SPOONACULAR_KEY:
        raise ValueError("SPOONACULAR_KEY не установлен!")

    # Создаём приложение
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Добавляем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Запускаем polling
    app.run_polling()

if __name__ == "__main__":
    main()
