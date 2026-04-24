import os
import telebot
import logging
from google import genai
from google.genai import types
from dotenv import load_dotenv

# load_dotenv нужен только если ты все же используешь .env локально. 
# На хостинге он не помешает.
load_dotenv()

# Настройка логирования (вывод в консоль хостинга)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ПОЛУЧЕНИЕ ТОКЕНОВ (На хостинге добавь их в разделе Environment Variables)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Проверка наличия ключей, чтобы бот не "молчал" при ошибке
if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    print("CRITICAL ERROR: Tokens not found! Check your Hosting Environment Variables.")
    exit(1)

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = genai.Client(api_key=GEMINI_API_KEY)

# Модель gemini-1.5-flash более стабильна для бесплатных аккаунтов
MODEL_ID = "gemini-1.5-flash"

def get_ai_answer(contents):
    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=contents
        )
        return response.text
    except Exception as e:
        logger.error(f"API Error: {e}")
        if "429" in str(e):
            return "⚠️ Слишком много запросов. Подождите немного."
        return "❌ Ошибка при связи с ИИ."

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.reply_to(message, "🤖 Бот успешно запущен на хостинге и готов к работе!")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    bot.send_chat_action(message.chat.id, 'typing')
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        prompt = message.caption or "Что на этом фото?"
        contents = [
            types.Part.from_bytes(data=downloaded_file, mime_type="image/jpeg"),
            prompt
        ]
        
        answer = get_ai_answer(contents)
        bot.reply_to(message, answer)
    except Exception as e:
        bot.reply_to(message, "Ошибка при обработке фото.")

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    bot.send_chat_action(message.chat.id, 'typing')
    try:
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        contents = [
            types.Part.from_bytes(data=downloaded_file, mime_type="audio/ogg"),
            "Ответь на это аудио."
        ]
        
        answer = get_ai_answer(contents)
        bot.reply_to(message, answer)
    except Exception as e:
        bot.reply_to(message, "Ошибка распознавания голоса.")

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    bot.send_chat_action(message.chat.id, 'typing')
    answer = get_ai_answer(message.text)
    bot.reply_to(message, answer)

if __name__ == "__main__":
    print(f"Starting bot on model {MODEL_ID}...")
    # infinity_polling — лучший выбор для хостинга, он не падает при сетевых ошибках
    bot.infinity_polling()