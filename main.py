import os
import logging
import requests
from telegram import Update
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters, CallbackContext
)
from fastapi import FastAPI, Request
import uvicorn

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

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
        logger.error(f"Ошибка при запросе к Spoonacular: {e}")
        update.message.reply_text(f"⚠️ Ошибка при поиске: {str(e)}")

def handle_photo(update: Update, context: CallbackContext):
    update.message.reply_text(
        "📸 Фото получено!\n"
        "⚠️ В бесплатной версии я пока распознаю только текст. "
        "Отправь название блюда словами — например, «гречка с курицей»."
    )

def error_handler(update: Update, context: CallbackContext):
    """Обработчик ошибок"""
    logger.error(f"Ошибка при обработке обновления: {context.error}")
    if update and update.message:
        update.message.reply_text("⚠️ Произошла ошибка. Попробуйте еще раз.")

# Создаём FastAPI приложение
app = FastAPI()

# Глобальные переменные для бота
updater = None
dispatcher = None

def setup_bot():
    """Инициализация бота"""
    global updater, dispatcher
    
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN не установлен!")
    if not SPOONACULAR_KEY:
        raise ValueError("SPOONACULAR_KEY не установлен!")
    
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    
    # Добавляем обработчики
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    dispatcher.add_handler(MessageHandler(Filters.photo, handle_photo))
    dispatcher.add_error_handler(error_handler)
    
    logger.info("Бот инициализирован")

@app.on_event("startup")
async def startup_event():
    """Запускаем бота при старте приложения"""
    setup_bot()
    
    # Устанавливаем вебхук на корневой URL (важно для Telegram!)
    webhook_url = os.environ.get("RAILWAY_STATIC_URL", "")
    if webhook_url:
        # Устанавливаем вебхук на корневой URL
        updater.bot.set_webhook(url=webhook_url)  # Без /webhook!
        logger.info(f"Вебхук установлен на корневой URL: {webhook_url}")
    else:
        # Для локальной разработки используем поллинг
        logger.info("Используется поллинг (локальная разработка)")
        updater.start_polling()
        updater.idle()

@app.post("/")
async def handle_webhook(request: Request):
    """Обработка вебхуков от Telegram (на корневом URL)"""
    try:
        # Получаем обновление
        update_data = await request.json()
        logger.info(f"Получено обновление: {update_data}")
        
        # Создаем объект Update
        update = Update.de_json(update_data, updater.bot)
        
        # Передаем обновление диспетчеру
        dispatcher.process_update(update)
        
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Ошибка при обработке вебхука: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/")
async def root_get():
    """Корневой эндпоинт для GET запросов"""
    return {"status": "bot is running", "service": "calorie-bot"}

@app.get("/health")
async def health_check():
    """Эндпоинт для проверки здоровья"""
    return {"status": "healthy"}

@app.get("/setwebhook")
async def set_webhook_manual():
    """Ручная установка вебхука (для отладки)"""
    try:
        webhook_url = os.environ.get("RAILWAY_STATIC_URL", "")
        if not webhook_url:
            return {"error": "RAILWAY_STATIC_URL не установлен"}
        
        # Сбрасываем вебхук
        updater.bot.delete_webhook()
        
        # Устанавливаем новый
        result = updater.bot.set_webhook(url=webhook_url)
        
        return {
            "status": "success",
            "webhook_url": webhook_url,
            "result": result
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    # Проверяем переменные окружения
    if not TELEGRAM_TOKEN or not SPOONACULAR_KEY:
        logger.error("Не установлены TELEGRAM_TOKEN или SPOONACULAR_KEY!")
        exit(1)
    
    # Запускаем сервер
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
