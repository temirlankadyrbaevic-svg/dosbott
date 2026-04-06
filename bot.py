import os
import psycopg2
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# --- БАПТАУЛАР ---
TOKEN = "8670502824:AAG7ZblOnd6o_-nIo6NKdYmfvtvv4vMyfrQ"
GEMINI_KEY = "AIzaSyChqar4CmaFHUBte_Se2cHH62xfsJw32s4"
# Supabase -> Settings -> Database -> Connection String (URI)
DATABASE_URL = "postgresql://postgres:[T_H/$?J-%&y4P7y]@db.your-id.supabase.co:5432/postgres"

# ЖИ баптау (Gemini 1.5 Flash - ең жылдам нұсқасы)
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Supabase-ке қосылу функциясы
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

# Кестені дайындау
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS users (id BIGINT PRIMARY KEY, lang TEXT DEFAULT "kz")')
    conn.commit()
    cur.close()
    conn.close()

# Тіл таңдау батырмалары
lang_kb = ReplyKeyboardMarkup(resize_keyboard=True).add(
    KeyboardButton("Қазақша 🇰🇿"), KeyboardButton("Русский 🇷🇺")
)

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO users (id) VALUES (%s) ON CONFLICT (id) DO NOTHING', (message.from_user.id,))
    conn.commit()
    cur.close()
    conn.close()
    await message.answer("Сәлем! Тілді таңдаңыз / Выберите язык:", reply_markup=lang_kb)

@dp.message_handler(lambda message: message.text in ["Қазақша 🇰🇿", "Русский 🇷🇺"])
async def set_lang(message: types.Message):
    lang = 'kz' if "Қазақша" in message.text else 'ru'
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('UPDATE users SET lang = %s WHERE id = %s', (lang, message.from_user.id))
    conn.commit()
    cur.close()
    conn.close()
    
    msg = "Енді мәселеңізді жаза беріңіз, мен сізге көмектесемін." if lang == 'kz' else "Теперь опишите вашу проблему, я помогу вам."
    await message.answer(msg, reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler()
async def ai_chat(message: types.Message):
    # Пайдаланушының тілін дерекқордан алу
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT lang FROM users WHERE id = %s', (message.from_user.id,))
    res = cur.fetchone()
    cur.close()
    conn.close()
    
    user_lang = res[0] if res else 'kz'

    # ЖИ-ге контекст беру (Психолог рөлі)
    system_instruction = (
        "Сен мектеп психологысың. Буллингке ұшыраған балаларға эмпатиямен жауап бер. "
        f"Жауапты тек {('қазақ тілінде' if user_lang == 'kz' else 'на русском языке')} бер."
    )

    try:
        # Gemini-ден жауап алу
        chat_session = model.start_chat(history=[])
        full_prompt = f"{system_instruction}\n\nПайдаланушы: {message.text}"
        response = model.generate_content(full_prompt)
        
        await message.answer(response.text)
        
    except Exception as e:
        error_text = "Кешіріңіз, байланыс үзілді. Қайта жазып көріңіз." if user_lang == 'kz' else "Ошибка связи с ИИ. Попробуйте еще раз."
        await message.answer(f"{error_text}\n(Техникалық қате: {str(e)})")

if __name__ == '__main__':
    init_db()
    executor.start_polling(dp, skip_updates=True)
