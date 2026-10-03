import os
import logging
from magic_hour import Client
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ============================================
# ЗАМЕНИ ЭТИ ДВЕ СТРОКИ НА СВОИ КЛЮЧИ:
# ============================================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MAGIC_HOUR_API_KEY = os.environ.get("MAGIC_HOUR_API_KEY")
# ============================================

# Модель: wan-2.2 — бесплатная, 480p, 5 секунд
MODEL = "wan-2.2"
DURATION = 5
RESOLUTION = "480p"
ASPECT_RATIO = "16:9"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот для генерации видео. 🎬\n"
        "Напиши мне описание того, что хочешь увидеть, и я пришлю видео."
    )

async def generate_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = update.message.text
    await update.message.reply_text(f"🎬 Запускаю генерацию: «{prompt}»\nЭто может занять пару минут...")

    try:
        client = Client(token=MAGIC_HOUR_API_KEY)

        # Одна команда generate() — SDK сам создаёт задачу, ждёт и скачивает файл
        response = client.v1.text_to_video.generate(
            style={"prompt": prompt},
            model=MODEL,
            end_seconds=DURATION,
            resolution=RESOLUTION,
            aspect_ratio=ASPECT_RATIO,
            name="Telegram video",
            wait_for_completion=True,
            download_outputs=False,  # не скачиваем, просто берём URL
        )

        # Получаем URL готового видео
        if hasattr(response, 'downloads') and response.downloads:
            video_url = response.downloads[0].url
            await update.message.reply_video(video=video_url, caption="Готово! 🎉")
        else:
            await update.message.reply_text("⚠️ Видео готово, но ссылку получить не удалось.")

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        error_text = str(e)
        if "insufficient_credits" in error_text.lower():
            await update.message.reply_text("⚠️ Закончились бесплатные кредиты Magic Hour. Попробуй позже.")
        else:
            await update.message.reply_text(f"❌ Ошибка: {error_text[:200]}")

if __name__ == '__main__':
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generate_video))
    print("Бот запущен...")
    application.run_polling()
