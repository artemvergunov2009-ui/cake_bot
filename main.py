import telebot
from telebot import types
import sqlite3
from datetime import datetime

# === НАСТРОЙКИ ===
TOKEN = '8715296684:AAGxIpK2we9Gts6ebffo-RgCnyT14bTgmyI'
ADMIN_ID = 7070204958  # Замени на свой Telegram ID (числом)

bot = telebot.TeleBot(TOKEN)

# === РАБОТА С БАЗОЙ ДАННЫХ ===
def init_db():
    conn = sqlite3.connect('updater_bot.db')
    cursor = conn.cursor()
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY
        )
    ''')
    # Таблица обновлений
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id TEXT,
            caption TEXT,
            version_date TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_user(user_id):
    conn = sqlite3.connect('updater_bot.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect('updater_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users

def save_update(file_id, caption, version_date):
    conn = sqlite3.connect('updater_bot.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO updates (file_id, caption, version_date) VALUES (?, ?, ?)', 
                   (file_id, caption, version_date))
    conn.commit()
    conn.close()

def get_latest_update():
    conn = sqlite3.connect('updater_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT file_id, caption, version_date FROM updates ORDER BY id DESC LIMIT 1')
    res = cursor.fetchone()
    conn.close()
    return res

# === ВРЕМЕННОЕ ХРАНИЛИЩЕ ДЛЯ АДМИНА ===
admin_states = {}

# === КЛАВИАТУРЫ ===
def main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔄 Проверить обновление"))
    if user_id == ADMIN_ID:
        markup.add(types.KeyboardButton("📤 Выгрузить обновление"))
    return markup

# === ХЕНДЛЕРЫ ===
@bot.message_handler(commands=['start'])
def start_cmd(message):
    add_user(message.chat.id)
    bot.send_message(
        message.chat.id, 
        "Привет! Здесь ты можешь скачать актуальную версию нашего мессенджера.", 
        reply_markup=main_keyboard(message.chat.id)
    )

@bot.message_handler(func=lambda msg: msg.text == "🔄 Проверить обновление")
def check_update(message):
    last_update = get_latest_update()
    if not last_update:
        bot.send_message(message.chat.id, "Обновлений пока нет.")
        return
    
    file_id, caption, version_date = last_update
    text = f"📅 **Дата версии:** {version_date}\n\n📝 **Что нового:**\n{caption}"
    
    bot.send_document(message.chat.id, file_id, caption=text, parse_mode='Markdown')

# --- АДМИНСКАЯ ЧАСТЬ ---
@bot.message_handler(func=lambda msg: msg.text == "📤 Выгрузить обновление" and msg.from_user.id == ADMIN_ID)
def start_upload(message):
    admin_states[message.chat.id] = {'step': 'waiting_apk'}
    bot.send_message(message.chat.id, "Отправь мне `.apk` файл обновления:")

@bot.message_handler(content_types=['document'], func=lambda msg: admin_states.get(msg.chat.id, {}).get('step') == 'waiting_apk')
def handle_apk(message):
    if not message.document.file_name.endswith('.apk'):
        bot.send_message(message.chat.id, "❌ Это не APK-файл. Пожалуйста, отправь файл с расширением .apk")
        return
    
    admin_states[message.chat.id]['file_id'] = message.document.file_id
    admin_states[message.chat.id]['step'] = 'waiting_caption'
    bot.send_message(message.chat.id, "Файл получен. Теперь напиши **комментарий (чейнджлог)** к обновлению:")

@bot.message_handler(func=lambda msg: admin_states.get(msg.chat.id, {}).get('step') == 'waiting_caption')
def handle_caption(message):
    admin_states[message.chat.id]['caption'] = message.text
    admin_states[message.chat.id]['step'] = 'waiting_date'
    
    # Автоматически предлагаем сегодняшнюю дату, но админ может написать свою
    today = datetime.now().strftime("%d.%m.%Y")
    bot.send_message(message.chat.id, f"Введите дату/версию обновления (например, `{today}`):", parse_mode='Markdown')

@bot.message_handler(func=lambda msg: admin_states.get(msg.chat.id, {}).get('step') == 'waiting_date')
def handle_date_and_broadcast(message):
    data = admin_states.get(message.chat.id)
    version_date = message.text
    file_id = data['file_id']
    caption = data['caption']
    
    # Сохраняем в БД
    save_update(file_id, caption, version_date)
    
    bot.send_message(message.chat.id, "🚀 Начинаю рассылку обновления подписчикам...")
    
    # Рассылка
    users = get_all_users()
    success_count = 0
    
    for u_id in users:
        try:
            text = f"🚀 **Вышло новое обновление!**\n\n📅 **Дата:** {version_date}\n📝 **Что нового:**\n{caption}"
            bot.send_document(u_id, file_id, caption=text, parse_mode='Markdown')
            success_count += 1
        except Exception as e:
            print(f"Не удалось отправить пользователю {u_id}: {e}")
            
    bot.send_message(message.chat.id, f"✅ Рассылка завершена. Успешно отправлено: {success_count}/{len(users)}")
    del admin_states[message.chat.id] # Очищаем состояние

# === ЗАПУСК ===
if __name__ == '__main__':
    init_db()
    print("Бот запущен...")
    bot.infinity_polling()
