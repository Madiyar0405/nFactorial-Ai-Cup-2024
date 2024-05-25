import logging
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv

import google.generativeai as genai

load_dotenv()

api = os.getenv('API')
bot_api = os.getenv('BOT_API')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)

# Ваш API ключ Google Generative AI
genai.configure(api_key=api)

# Настройки модели
generation_config = {
  "temperature": 0.7, 
  "top_p": 0.95,
  "top_k": 64,
  "max_output_tokens": 512,
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

# Переменная для хранения регламента
reglament = ""

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text="Привет! Я бот-модератор. Чтобы я мог отвечать на ваши вопросы, отправьте мне регламент мероприятия командой /reglament."
    )

# Обработчик команды /reglament
async def set_reglament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global reglament
    reglament = update.message.text[11:].strip() # Убираем "/reglament "
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Регламент получен! Теперь я могу отвечать на вопросы."
    )

# Обработчик сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    
    # Формируем запрс к модели с учетом регламента
    prompt = f"Регламент мероприятия:\n\n{reglament}\n\nВопрос: {user_message}\n\nОтвет:"

    response = model.generate_content(prompt) # <--- Исправленная строка
    await context.bot.send_message(chat_id=update.effective_chat.id, text=response.text)

# Запуск бота
if __name__ == '__main__':
    application = ApplicationBuilder().token(bot_api).build()
    
    start_handler = CommandHandler('start', start)
    reglament_handler = CommandHandler('reglament', set_reglament)
    message_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    
    application.add_handler(start_handler)
    application.add_handler(reglament_handler)
    application.add_handler(message_handler)
    
    application.run_polling()