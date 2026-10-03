import os
import logging
import time
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
AGNES_API_KEY = os.environ.get("AGNES_API_KEY")

AGNES_BASE_URL = "https://apihub.agnes-ai.com/v1"

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
    payload = {
        "model": "agnes-video-2.0",
        "prompt": prompt
    }

    try:
        response = requests.post(f"{AGNES_BASE_URL}/videos", json=payload, headers=headers)
        response.raise_for_status()
        task_data = response.json()
        task_id = task_data.get("id")

        if not task_id:
            await update.message.reply_text("❌ Не удалось получить ID задачи. Проверь ключ API.")
            return

        video_url = None
        for _ in range(60):
            time.sleep(5)
            status_resp = requests.get(f"{AGNES_BASE_URL}/videos/{task_id}", headers=headers)
            status_data = status_resp.json()
            status = status_data.get("status")

            if status == "completed":
                video_url = status_data.get("url")
                break
            elif status == "failed":
                await update.message.reply_text("❌ Ошибка генерации. Попробуй другой промпт.")
                return

        if video_url:
            await update.message.reply_video(video=video_url, caption="Готово! 🎉")
        else:
            await update.message.reply_text("⏳ Генерация занимает слишком много времени. Попробуй позже.")

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)[:100]}")

if __name__ == '__main__':
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generate_video))
    print("Бот запущен...")
    application.run_polling()
