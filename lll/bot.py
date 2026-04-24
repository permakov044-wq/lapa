import telebot
from google import genai
from google.genai import types
import os
import time

# ==== КОНФИГУРАЦИЯ (Вставь свои данные) ====
TELEGRAM_TOKEN = ""
GEMINI_API_KEY = ""

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = genai.Client(api_key=GEMINI_API_KEY)

# Настройка модели: 1.5-flash более стабильна для бесплатных аккаунтов
MODEL_NAME = "gemini-1.5-flash"

def call_gemini_with_retry(model, contents, config=None):
    """
    Функция для вызова Gemini с автоматическими повторами при ошибке 429 (лимиты).
    Реализует экспоненциальный откат: 1с, 2с, 4с, 8с, 16с.
    """
    retries = 5
    for i in range(retries):
        try:
            return client.models.generate_content(model=model, contents=contents, config=config)
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                if i < retries - 1:
                    wait_time = 2 ** i
                    print(f"Лимит исчерпан. Повтор через {wait_time} сек...")
                    time.sleep(wait_time)
                    continue
            raise e

def process_media_and_respond(message, file_path, mime_type, prompt):
    """Общая логика для обработки фото, видео и аудио."""
    try:
        with open(file_path, "rb") as f:
            file_data = f.read()
        
        contents = [
            types.Part.from_bytes(data=file_data, mime_type=mime_type),
            prompt if prompt else "Что здесь изображено или сказано?"
        ]
        
        response = call_gemini_with_retry(model=MODEL_NAME, contents=contents)
        bot.reply_to(message, response.text)
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {str(e)}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

# --- ОБРАБОТКА ТЕКСТА ---
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    bot.send_chat_action(message.chat.id, 'typing')
    try:
        response = call_gemini_with_retry(model=MODEL_NAME, contents=message.text)
        bot.reply_to(message, response.text)
    except Exception as e:
        bot.reply_to(message, "Извини, я временно перегружен. Попробуй написать через минуту.")

# --- ОБРАБОТКА ФОТО ---
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    bot.send_chat_action(message.chat.id, 'typing')
    file_info = bot.get_file(message.photo[-1].file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    path = "temp_img.jpg"
    with open(path, 'wb') as f:
        f.write(downloaded_file)
    
    caption = message.caption or "Опиши картинку подробно."
    process_media_and_respond(message, path, "image/jpeg", caption)

# --- ОБРАБОТКА ГОЛОСОВЫХ ---
@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    bot.send_chat_action(message.chat.id, 'typing')
    file_info = bot.get_file(message.voice.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    path = "temp_audio.ogg"
    with open(path, 'wb') as f:
        f.write(downloaded_file)
    
    process_media_and_respond(message, path, "audio/ogg", "Прослушай и ответь текстом.")

# --- ОБРАБОТКА ВИДЕО ---
@bot.message_handler(content_types=['video'])
def handle_video(message):
    bot.send_message(message.chat.id, "Анализирую видео, подождите...")
    file_info = bot.get_file(message.video.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    path = "temp_video.mp4"
    with open(path, 'wb') as f:
        f.write(downloaded_file)
    
    caption = message.caption or "Что происходит на видео?"
    process_media_and_respond(message, path, "video/mp4", caption)

if __name__ == "__main__":
    print(f"Бот запущен на модели {MODEL_NAME}...")
    bot.infinity_polling()