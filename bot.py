import sqlite3
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Конфигурация
API_TOKEN = '8618857277:AAGihYdR06pGYgPbb-7FAxHzbE4K-2nNZXY'
GENAI_API_KEY = 'AIzaSyChqar4CmaFHUBte_Se2cHH62xfsJw32s4'

# ЖИ баптау
genai.configure(api_key=GENAI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Дерекқор (Тілді және статистиканы сақтау)
conn = sqlite3.connect('bullying_bot.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                  (id INTEGER PRIMARY KEY, lang TEXT)''')
conn.commit()

# Тіл таңдау батырмалары
lang_keyboard = ReplyKeyboardMarkup(resize_keyboard=True).add(
    KeyboardButton("Қазақша 🇰🇿"), KeyboardButton("Русский 🇷🇺")
)

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    cursor.execute('INSERT OR IGNORE INTO users (id) VALUES (?)', (message.from_user.id,))
    conn.commit()
    await message.answer("Сәлем! Тілді таңдаңыз / Выберите язык:", reply_markup=lang_keyboard)

@dp.message_handler(lambda message: message.text in ["Қазақша 🇰🇿", "Русский 🇷🇺"])
async def set_language(message: types.Message):
    lang = 'kz' if "Қазақша" in message.text else 'ru'
    cursor.execute('UPDATE users SET lang = ? WHERE id = ?', (lang, message.from_user.id))
    conn.commit()
    
    msg = "Мәселеңізді жазыңыз, мен сізді тыңдап тұрмын..." if lang == 'kz' else "Опишите вашу проблему, я вас слушаю..."
    await message.answer(msg, reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(commands=['stats'])
async def show_stats(message: types.Message):
    cursor.execute('SELECT COUNT(*) FROM users')
    count = cursor.fetchone()[0]
    await message.answer(f"Жалпы қолданушылар саны: {count}")

@dp.message_handler()
async def handle_message(message: types.Message):
    cursor.execute('SELECT lang FROM users WHERE id = ?', (message.from_user.id,))
    res = cursor.fetchone()
    lang = res[0] if res else 'kz'

    # ЖИ-ге нұсқаулық (System Instruction)
    prompt_context = (
        "Сен мектептегі буллингке қарсы көмек беретін психологсың. "
        "Жауабың жұмсақ, қолдау көрсететіндей және эмпатияға толы болуы керек. "
        "Балаға зиян тигізбейтін кеңестер бер. Жауапты мына тілде бер: " + ("Қазақша" if lang == 'kz' else "Русский")
    )
    
    full_prompt = f"{prompt_context}\n\nПайдаланушы мәселесі: {message.text}"
    
    try:
        response = model.generate_content(full_prompt)
        await message.answer(response.text)
    except Exception:
        error_msg = "Кешіріңіз, қазір байланыс қиындап тұр." if lang == 'kz' else "Извините, возникли проблемы со связью."
        await message.answer(error_msg)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
