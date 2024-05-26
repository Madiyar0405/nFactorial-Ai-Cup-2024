import json
import logging
import os
from telegram import Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

api = os.getenv('API')
bot_api = os.getenv('BOT_API')


REGULATIONS_FILE = 'regulations.json'

def load_regulations():
    try:
        with open(REGULATIONS_FILE, 'r', encoding='utf-8') as f:
            data = f.read()
    
            if data: 
                return json.loads(data)  
            else:
                return {}  
    except FileNotFoundError:
        return {}  

# Функция для сохранения регламентов в JSON-файл
def save_regulations(regulations_data):
    with open(REGULATIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(regulations_data, f, indent=4, ensure_ascii=False)


regulations = load_regulations()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)


genai.configure(api_key=api)

# Настройки модели
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 2048,
    "response_mime_type": "text/plain",
}
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

# Создание модели
model = genai.GenerativeModel(
    model_name="gemini-1.5-pro",
    safety_settings=safety_settings,
    generation_config=generation_config,
)


organizer_chat_id = 704255878


chat_permissions = None
chat_id = None


def load_prompt(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Привет! Я умный бот, который может отвечать на ваши вопросы. \n\n"
             "Я умею:\n"
             "- Отвечать на вопросы на различные темы.\n"
             "- Генерировать креативный текст.\n"
             "- Переводить текст.\n"
             "- И многое другое!\n\n"
             "Чтобы задать мне вопрос, просто напишите его в чат."
    )

    # Добавление кнопки "Добавить в чат"
    keyboard = [
        [InlineKeyboardButton("Добавить меня в чат", url=f"https://t.me/modrr_bot?startgroup=AddToGroup")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Хотите добавить меня в свой чат? Нажмите кнопку ниже:",
        reply_markup=reply_markup
    )

async def upload_regulations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_type = update.effective_chat.type

    logging.info(f"Получена команда /upload_regulations от пользователя {user_id}, тип чата: {chat_type}")
    print(f"Тип чата: {chat_type}")

    if chat_type != constants.ChatType.PRIVATE:
        logging.info("Команда /upload_regulations не из личного чата, игнорируем.")
        return

    # Проверяем, был ли уже загружен регламент для этого пользователя
    if context.user_data.get('regulations_loaded', False):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Вы уже загрузили регламент.")
        return

    await context.bot.send_message(chat_id=update.effective_chat.id, text="Пожалуйста, отправьте текст регламента:")
    return 1  # Ожидаем текст регламента


async def save_regulations_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global regulations
    regulations["default_regulations"] = update.message.text  # Сохраняем регламент с фиксированным ключом
    save_regulations(regulations)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Регламент успешно загружен!")
    
    # Устанавливаем флаг, что регламент загружен
    context.user_data['regulations_loaded'] = True 

    return ConversationHandler.END

# Обработчик сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global regulations
    user_message = update.message.text
    chat_type = update.effective_chat.type
    chat_id = update.effective_chat.id

    if chat_type in [constants.ChatType.GROUP, constants.ChatType.SUPERGROUP]:
        # Всегда используем регламент, сохраненный по ключу "default_regulations"
        if "default_regulations" in regulations: 
            regulations_text = regulations["default_regulations"]
            system_prompt = load_prompt('prompt.txt')
            prompt = f"{system_prompt}\n\nРегламент:\n{regulations_text}\n\nВопрос: {user_message}\n\nОтвет:"
            response = model.generate_content(prompt)
            await context.bot.send_message(chat_id=update.effective_chat.id, text=response.text)
        else:
            await context.bot.send_message(chat_id=chat_id,
                                           text="Регламент не найден. Пожалуйста, обратитесь к организатору.")

# Обработчик добавления бота в группу
async def add_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global chat_permissions, chat_id
    chat_id = update.effective_chat.id

    # Настройка прав бота в чате
    chat_permissions = ChatPermissions(
        can_send_messages=True,
        can_send_media_messages=True,
        can_send_polls=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True,
        can_invite_users=True,
        can_pin_messages=False,
    )
    await context.bot.set_chat_permissions(
        chat_id=chat_id,
        permissions=chat_permissions
    )
    await context.bot.send_message(
        chat_id=chat_id,
        text="Теперь я в вашем чате! Задавайте мне вопросы, я готов отвечать!"
    )

# Запуск бота
if __name__ == '__main__':

    application = ApplicationBuilder().token(bot_api).build()
    # Добавляем обработчики
    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)

    # ConversationHandler для загрузки регламента
    regulations_handler = ConversationHandler(
        entry_points=[CommandHandler('upload_regulations', upload_regulations)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_regulations_handler)],
        },
        fallbacks=[],
        per_user=True,  # Добавляем per_user=True
        per_chat=False, # Добавляем per_chat=False
    )
    application.add_handler(regulations_handler)

    message_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    add_to_group_handler = MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, add_to_group)
    application.add_handler(message_handler)
    application.add_handler(add_to_group_handler)
    application.run_polling()
