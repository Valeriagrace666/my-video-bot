import os
import logging
from magic_hour import Client
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- ЗАМЕНИ ЭТО НА СВОЙ ТОКЕН ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MAGIC_HOUR_API_KEY = os.environ.get("MAGIC_HOUR_API_KEY")
# --------------------------------

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ==================== МЕНЮ ====================
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("🎬 Сгенерировать видео", callback_data="menu_text_video")],
        [InlineKeyboardButton("🖼 Оживить фото", callback_data="menu_image_video")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['mode'] = None
    await update.message.reply_text(
        "Привет! Я бот для генерации видео. 🎬\n"
        "Выбери, что хочешь сделать:",
        reply_markup=get_main_menu()
    )

# ==================== ОБРАБОТКА КНОПОК ====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "menu_text_video":
        context.user_data['mode'] = 'text'
        await query.edit_message_text("✏️ Напиши текстовое описание видео:")
    elif query.data == "menu_image_video":
        context.user_data['mode'] = 'image'
        await query.edit_message_text("📸 Отправь фото, которое хочешь оживить:")

# ==================== ГЕНЕРАЦИЯ ИЗ ТЕКСТА ====================
async def generate_from_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = update.message.text
    await update.message.reply_text(f"🎬 Запускаю генерацию: «{prompt}»\nЭто может занять пару минут...")

    try:
        client = Client(token=MAGIC_HOUR_API_KEY)

        result = client.v1.text_to_video.generate(
            style={"prompt": prompt},
            model="wan-2.2",  # Бесплатная модель
            end_seconds=5,
            resolution="480p",
            aspect_ratio="9:16",  # Вертикальное видео
            name="Telegram text video",
            wait_for_completion=True,
            download_outputs=False,
        )

        if hasattr(result, 'downloads') and result.downloads:
            video_url = result.downloads[0].url
            await update.message.reply_video(video=video_url, caption="Готово! 🎉")
        else:
            await update.message.reply_text("⚠️ Видео готово, но ссылку получить не удалось.")

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)[:200]}")

# ==================== ГЕНЕРАЦИЯ ИЗ ФОТО ====================
async def generate_from_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await photo.get_file()

    local_path = f"/tmp/{photo.file_unique_id}.jpg"
    await file.download_to_drive(local_path)

    prompt = update.message.caption if update.message.caption else "Animate this image with cinematic motion"

    await update.message.reply_text(f"🖼 Оживляю фото...\nПромпт: «{prompt}»\nЭто может занять пару минут...")

    try:
        client = Client(token=MAGIC_HOUR_API_KEY)

        result = client.v1.image_to_video.generate(
            assets={"image_file_path": local_path},
            style={"prompt": prompt},
            model="ltx-2.3",  # Бесплатная модель
            end_seconds=5,
            resolution="480p",
            name="Telegram image video",
            wait_for_completion=True,
            download_outputs=False,
        )

        if hasattr(result, 'downloads') and result.downloads:
            video_url = result.downloads[0].url
            await update.message.reply_video(video=video_url, caption="Готово! 🎉")
        else:
            await update.message.reply_text("⚠️ Видео готово, но ссылку получить не удалось.")

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)[:200]}")

# ==================== РОУТИНГ ====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get('mode')

    if mode == 'text':
        await generate_from_text(update, context)
    elif mode == 'image':
        await generate_from_image(update, context)
    else:
        await update.message.reply_text(
            "Сначала выбери действие:",
            reply_markup=get_main_menu()
        )

# ==================== ЗАПУСК ====================
if __name__ == '__main__':
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.PHOTO, generate_from_image))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот запущен...")
    application.run_polling()
