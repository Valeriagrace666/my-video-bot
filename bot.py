import os
import logging
import base64
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GIGACHAT_AUTH_KEY = os.environ.get("GIGACHAT_AUTH_KEY")
GIGACHAT_SCOPE = os.environ.get("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ==================== ПОЛУЧЕНИЕ ТОКЕНА GIGACHAT ====================
def get_gigachat_token():
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "RqUID": "6f0b1291-9a3e-4c7c-8e8f-2c4e5e6f7a8b",  # любой UUID
        "Authorization": f"Basic {GIGACHAT_AUTH_KEY}"
    }
    payload = {"scope": GIGACHAT_SCOPE}
    response = requests.post(url, headers=headers, data=payload, verify=False)
    return response.json().get("access_token")

# ==================== ГЕНЕРАЦИЯ ПРОМПТА ====================
def generate_prompt(user_idea, style):
    token = get_gigachat_token()
    if not token:
        return None

    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    prompt_text = (
        f"Ты — профессиональный промпт-инженер. Пользователь хочет создать изображение. "
        f"Его идея: «{user_idea}». Стиль: {style}. "
        f"Сгенерируй один очень подробный, детальный промпт на русском языке (150-200 слов). "
        f"Опиши сюжет, композицию, освещение, цвета, детали, атмосферу. "
        f"Выдай только текст промпта, без пояснений."
    )
    payload = {
        "model": "GigaChat",
        "messages": [{"role": "user", "content": prompt_text}],
        "temperature": 0.7
    }
    response = requests.post(url, headers=headers, json=payload, verify=False)
    return response.json()["choices"][0]["message"]["content"]

# ==================== МЕНЮ ====================
def main_menu():
    keyboard = [
        [InlineKeyboardButton("✨ Создать промпт для картинки", callback_data="create_prompt")],
        [InlineKeyboardButton("📖 Как пользоваться", callback_data="help")],
    ]
    return InlineKeyboardMarkup(keyboard)

def style_menu():
    keyboard = [
        [InlineKeyboardButton("Реализм", callback_data="style_реализм")],
        [InlineKeyboardButton("Аниме", callback_data="style_аниме")],
        [InlineKeyboardButton("Киберпанк", callback_data="style_киберпанк")],
        [InlineKeyboardButton("Фэнтези", callback_data="style_фэнтези")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== КОМАНДЫ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я помогу тебе создать крутой промпт для картинки. 🎨\n"
        "Выбери действие:",
        reply_markup=main_menu()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Как пользоваться:*\n\n"
        "1. Нажми «✨ Создать промпт для картинки».\n"
        "2. Выбери стиль.\n"
        "3. Напиши свою идею (например, «кот в космосе»).\n"
        "4. Получи готовый детальный промпт.\n"
        "5. Скопируй его и вставь в Шедеврум или Kandinsky — там сгенерируй картинку.\n\n"
        "🔗 *Ссылки:*\n"
        "• Шедеврум: https://shedevrum.ai\n"
        "• Kandinsky: https://gigachat.ru\n\n"
        "💡 Чем подробнее ты опишешь идею, тем лучше будет результат!",
        parse_mode='Markdown'
    )

# ==================== ОБРАБОТКА КНОПОК ====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "create_prompt":
        await query.edit_message_text("Выбери стиль для картинки:", reply_markup=style_menu())
    elif data == "back_to_menu":
        await query.edit_message_text("Выбери действие:", reply_markup=main_menu())
    elif data == "help":
        await query.edit_message_text(
            "📖 *Как пользоваться:*\n\n"
            "1. Нажми «✨ Создать промпт».\n"
            "2. Выбери стиль.\n"
            "3. Напиши идею.\n"
            "4. Получи промпт и вставь его в Шедеврум или Kandinsky.\n\n"
            "🔗 Шедеврум: https://shedevrum.ai\n"
            "🔗 Kandinsky: https://gigachat.ru",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]])
        )
    elif data.startswith("style_"):
        style = data.split("_")[1]
        context.user_data['style'] = style
        await query.edit_message_text(f"Стиль: *{style}*\n\n✏️ Напиши свою идею для картинки:", parse_mode='Markdown')

# ==================== ГЕНЕРАЦИЯ ====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'style' not in context.user_data:
        await update.message.reply_text("Сначала выбери действие:", reply_markup=main_menu())
        return

    user_idea = update.message.text
    style = context.user_data['style']
    await update.message.reply_text("⏳ Генерирую промпт...")

    try:
        prompt = generate_prompt(user_idea, style)
        if prompt:
            keyboard = [
                [InlineKeyboardButton("🎨 Шедеврум", url="https://shedevrum.ai")],
                [InlineKeyboardButton("💎 Kandinsky", url="https://gigachat.ru")],
            ]
            await update.message.reply_text(
                f"✨ *Готовый промпт:*\n\n{prompt}\n\n"
                f"👇 Скопируй его и вставь в один из сервисов:",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_text("❌ Не удалось получить токен GigaChat. Проверь ключ.")
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)[:200]}")

# ==================== ЗАПУСК ====================
if __name__ == '__main__':
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Бот запущен...")
    application.run_polling()
