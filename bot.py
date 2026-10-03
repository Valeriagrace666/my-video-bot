import os
import logging
import time
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- ЗАМЕНИ ЭТО НА СВОЙ ТОКЕН ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
AGNES_API_KEY = os.environ.get("AGNES_API_KEY")
# --------------------------------

AGNES_BASE_URL = "https://apihub.agnes-ai.com"
AGNES_MODEL = "agnes-video-2.5-flash"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот для генерации видео. 🎬\n"
        "Напиши мне описание того, что хочешь увидеть, и я пришлю видео."
    )

async def generate_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = update.message.text
    await update.message.reply_text(f"🎬 Запускаю генерацию: «{prompt}»\nЭто может занять пару минут...")

    headers = {
        "Authorization": f"Bearer {AGNES_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Новый формат запроса для 2.5-flash
    payload = {
        "model": AGNES_MODEL,
        "prompt": prompt,
        "seconds": "5",
        "mode": "text",
        "size": "720P",
        "aspect_ratio": "16:9"
    }

    try:
        response = requests.post(f"{AGNES_BASE_URL}/v1/videos", json=payload, headers=headers)
        response.raise_for_status()
        task_data = response.json()
        
        # Получаем video_id (в новом API может быть id или video_id)
        video_id = task_data.get("video_id") or task_data.get("id")

        if not video_id:
            await update.message.reply_text(f"❌ Не удалось получить ID задачи. Ответ сервера: {task_data}")
            return

        # Опрос статуса
        video_url = None
        # Ждём максимум ~5 минут (60 попыток по 5 секунд)
        for i in range(60):
            time.sleep(5)
            # Новый эндпоинт для проверки статуса
            poll_url = f"{AGNES_BASE_URL}/agnesapi?video_id={video_id}&model_name={AGNES_MODEL}"
            status_resp = requests.get(poll_url, headers=headers)
            status_data = status_resp.json()
            
            status = status_data.get("status", "").lower()
            progress = status_data.get("progress", 0)
            
            # Обновляем сообщение о прогрессе (опционально)
            if status in ["queued", "in_progress"]:
                continue # Просто ждём
            
            if status in ["completed", "done", "success"]:
                video_url = status_data.get("url") or status_data.get("video_url")
                break
            elif status in ["failed", "error"]:
                error_msg = status_data.get("error", "Неизвестная ошибка")
                await update.message.reply_text(f"❌ Ошибка генерации: {error_msg}")
                return

        if video_url:
            await update.message.reply_video(video=video_url, caption="Готово! 🎉")
        else:
            await update.message.reply_text("⏳ Генерация занимает слишком много времени. Попробуй позже.")

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        # Показываем часть ответа сервера для понимания ошибки
        error_details = str(e)
        await update.message.reply_text(f"❌ Ошибка: {error_details[:200]}")

if __name__ == '__main__':
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generate_video))
    print("Бот запущен...")
    application.run_polling()
