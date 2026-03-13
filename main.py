import telebot
from telebot import types
import math 
import os
import time 
from supabase import create_client, Client

# === ТВОИ НАСТРОЙКИ ===
TOKEN = "8797133518:AAE1FWqCJeqS1vkHVC-PW5ztYx2xEC6Rw4A"
MAIN_ADMIN_ID = 7070204958  # <-- ТВОЙ ID (ГЛАВНЫЙ АДМИН)

# === НАСТРОЙКИ SUPABASE ===
SUPABASE_URL = "https://ktbvzocvmpnhxzvrfhqt.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imt0YnZ6b2N2bXBuaHh6dnJmaHF0Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MzQxMDg4MywiZXhwIjoyMDg4OTg2ODgzfQ.8I3TUXFQsyaeLt49BefXyzUcLygMpi_P7nNrJZi76Q0"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

bot = telebot.TeleBot(TOKEN)

# === НАСТРОЙКИ ДОСТАВКИ ===
SHOP_LAT = 55.5658  
SHOP_LON = 37.6033  
BASE_DELIVERY = 200 
PRICE_PER_KM = 50   

DEFAULT_CATALOG = {
    "bento": {"name": "Бенто-торт 🎂", "price": 1500, "desc": "Вес 400г. Идеально на 1-2 человек.", "photo": []},
    "cupcakes": {"name": "Капкейки (6 шт) 🧁", "price": 1200, "desc": "Нежные бисквиты с шапочкой из крем-чиза.", "photo": []},
    "trifles": {"name": "Трайфлы (4 шт) 🍨", "price": 1000, "desc": "Порционные десерты в стаканчиках. Очень нежные и сочные.", "photo": []},
    "meringue": {"name": "Меренговый рулет ☁️", "price": 1300, "desc": "Воздушная меренга с кремом маскарпоне и свежими ягодами.", "photo": []},
    "cakebig": {"name": "Торт (от 2 кг) 🍰", "price": 3500, "desc": "Большой торт для вашего праздника. Цена указана за 2 кг.", "photo": []},
    
    "bakeryquiche": {"name": "Киш 🥧", "price": 900, "desc": "Сытный французский открытый пирог с нежной заливкой.", "photo": []},
    "bakerycabbage": {"name": "Пирожки с капустой 🥬", "price": 80, "desc": "Домашние пирожки с сочной капустой.", "photo": []},
    "bakerymeat": {"name": "Пирожки с мясом 🥩", "price": 100, "desc": "Сытные пирожки с мясной начинкой.", "photo": []},
    "bakerypotato": {"name": "Пирожки с картошкой 🥔", "price": 80, "desc": "Мягкие пирожки с картофельным пюре.", "photo": []},
    "bakerypizza": {"name": "Пицца 🍕", "price": 600, "desc": "Ароматная домашняя пицца с тянущимся сыром.", "photo": []},
    "bakerysamsa": {"name": "Самса 🥟", "price": 120, "desc": "Восточная самса с рубленым мясом и специями.", "photo": []},
    "bakerykulich": {"name": "Куличи 🥮", "price": 500, "desc": "Праздничный кулич с изюмом и глазурью.", "photo": []}
}

# ==========================================
# --- БАЗА ДАННЫХ SUPABASE ---
# ==========================================
def load_users():
    try:
        res = supabase.table('users').select('*').execute()
        return {str(r['chat_id']): r.get('username', '') for r in res.data}
    except: return {}

def save_user(from_user, chat_id):
    chat_id_str = str(chat_id)
    username = from_user.username.lower() if from_user.username else ""
    if chat_id_str not in known_users or known_users[chat_id_str] != username:
        known_users[chat_id_str] = username
        try: supabase.table('users').upsert({"chat_id": chat_id_str, "username": username}).execute()
        except: pass

def load_catalog():
    cat = DEFAULT_CATALOG.copy()
    try:
        res = supabase.table('catalog').select('*').execute()
        for r in res.data:
            cat[r['item_id']] = {"name": r.get('name', ''), "price": r.get('price', 0), "desc": r.get('desc_text', ''), "photo": r.get('photo', [])}
    except: pass
    return cat

def save_catalog_item(item_id, item_data):
    try:
        supabase.table('catalog').upsert({
            "item_id": item_id, "name": item_data.get("name", ""),
            "price": item_data.get("price", 0), "desc_text": item_data.get("desc", ""),
            "photo": item_data.get("photo", [])
        }).execute()
    except: pass

def delete_catalog_item(item_id):
    try: supabase.table('catalog').delete().eq('item_id', item_id).execute()
    except: pass

def load_admins():
    try:
        res = supabase.table('admins').select('*').execute()
        adms = [r['admin_id'] for r in res.data]
        if MAIN_ADMIN_ID not in adms: adms.append(MAIN_ADMIN_ID)
        return adms
    except: return [MAIN_ADMIN_ID]

def add_admin_db(adm_id):
    try: supabase.table('admins').upsert({"admin_id": adm_id}).execute()
    except: pass

def del_admin_db(adm_id):
    try: supabase.table('admins').delete().eq('admin_id', adm_id).execute()
    except: pass

def load_active_orders():
    try:
        res = supabase.table('active_orders').select('*').execute()
        return {r['order_id']: {"client_id": int(r['client_id']), "text": r['order_text']} for r in res.data}
    except: return {}

def save_active_order(order_id, client_id, text):
    try: supabase.table('active_orders').upsert({"order_id": order_id, "client_id": str(client_id), "order_text": text}).execute()
    except: pass

def delete_active_order(order_id):
    try: supabase.table('active_orders').delete().eq('order_id', order_id).execute()
    except: pass

def load_admin_rating():
    try:
        res = supabase.table('admin_rating').select('*').eq('id', 1).execute()
        if res.data: return {"total_score": res.data[0]['total_score'], "reviews_count": res.data[0]['reviews_count']}
    except: pass
    return {"total_score": 0, "reviews_count": 0}

def save_admin_rating():
    try: supabase.table('admin_rating').upsert({"id": 1, "total_score": admin_rating["total_score"], "reviews_count": admin_rating["reviews_count"]}).execute()
    except: pass

# ЗАГРУЗКА В ПАМЯТЬ ПРИ СТАРТЕ
known_users = load_users()
CATALOG = load_catalog()
ADMINS = load_admins()
active_orders = load_active_orders()
admin_rating = load_admin_rating()

for item_id, item_data in CATALOG.items():
    if 'photo' in item_data and isinstance(item_data['photo'], str): 
        item_data['photo'] = [item_data['photo']]

user_carts = {}
user_orders = {}
temp_admin_items = {} 
pending_orders_text = {} 
pending_receipts = {} 
user_last_media = {} 
active_support_chats = {} 

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371.0 
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    return round(R * 2 * math.asin(math.sqrt(math.sin((lat2 - lat1) / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2)**2)), 1)

def cleanup_media(chat_id):
    if chat_id in user_last_media:
        for m_id in user_last_media[chat_id]:
            try: bot.delete_message(chat_id, m_id)
            except: pass
        del user_last_media[chat_id]

# ==========================================
# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ И КНОПКИ ---
# ==========================================
def get_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🎂 Каталог"), types.KeyboardButton("🛒 Корзина"))
    markup.add(types.KeyboardButton("❓ Контакты и FAQ"), types.KeyboardButton("💬 Связаться с кондитером"))
    markup.add(types.KeyboardButton("🆘 Проблемы с ботом? Вызовите поддержку!"))
    
    if chat_id in ADMINS: 
        markup.add(types.KeyboardButton("📋 Активные заказы"), types.KeyboardButton("⚙️ Управление меню"))
        markup.add(types.KeyboardButton("📣 Рассылка"), types.KeyboardButton("🔄 Перезапуск"))
    
    if chat_id == MAIN_ADMIN_ID:
        markup.add(types.KeyboardButton("👥 Админы"), types.KeyboardButton("📊 Мой рейтинг"))
        markup.add(types.KeyboardButton("👥 Все пользователи"))
        
    return markup

def get_cancel_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔙 Отменить оформление"))
    return markup

def get_step_back_markup(extra_buttons=None):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if extra_buttons:
        for btn in extra_buttons: markup.add(types.KeyboardButton(btn))
    markup.add(types.KeyboardButton("🔙 Шаг назад"), types.KeyboardButton("🔙 Отменить оформление"))
    return markup

def get_photo_ready_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("✅ Готово"), types.KeyboardButton("🔙 Отменить оформление"))
    return markup

def get_address_markup(chat_id):
    addr = user_orders[chat_id].get('address', {})
    markup = types.InlineKeyboardMarkup()
    st = f"✅ {addr['street']}" if 'street' in addr else "❌ Город, улица и дом (Обязательно)"
    ap = f"✅ Кв: {addr['apt']}" if 'apt' in addr else "Квартира"
    en = f"✅ Под: {addr['ent']}" if 'ent' in addr else "Подъезд"
    fl = f"✅ Эт: {addr['floor']}" if 'floor' in addr else "Этаж"
    cm = f"✅ Коммент: {addr['com']}" if 'com' in addr else "Комментарий"
    
    markup.add(types.InlineKeyboardButton(f"📍 Адрес: {st}", callback_data="addr_street"))
    markup.add(types.InlineKeyboardButton(ap, callback_data="addr_apt"), types.InlineKeyboardButton(en, callback_data="addr_ent"), types.InlineKeyboardButton(fl, callback_data="addr_floor"))
    markup.add(types.InlineKeyboardButton(cm, callback_data="addr_com"))
    markup.add(types.InlineKeyboardButton("✅ АДРЕС ЗАПОЛНЕН", callback_data="addr_done"))
    return markup

def check_cancel(message):
    if message.text and (message.text == "🔙 Отменить оформление" or message.text == "❌ Отмена"):
        cleanup_media(message.chat.id) 
        bot.send_message(message.chat.id, "Действие отменено. Возвращаю в главное меню.", reply_markup=get_main_menu(message.chat.id))
        if message.chat.id in user_orders: del user_orders[message.chat.id]
        if message.chat.id in temp_admin_items: del temp_admin_items[message.chat.id]
        return True
    return False

def end_support_chat(chat_id):
    if chat_id not in active_support_chats: return
    partner_id = active_support_chats[chat_id]
    del active_support_chats[chat_id]
    if partner_id in active_support_chats: del active_support_chats[partner_id]
        
    bot.send_message(chat_id, "Диалог с поддержкой завершен.", reply_markup=get_main_menu(chat_id))
    bot.send_message(partner_id, "Диалог с поддержкой завершен.", reply_markup=get_main_menu(partner_id))
    
    client_id = chat_id if chat_id != MAIN_ADMIN_ID else partner_id
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("1⭐", callback_data="rate_1"), types.InlineKeyboardButton("2⭐", callback_data="rate_2"), types.InlineKeyboardButton("3⭐", callback_data="rate_3"), types.InlineKeyboardButton("4⭐", callback_data="rate_4"), types.InlineKeyboardButton("5⭐", callback_data="rate_5"))
    bot.send_message(client_id, "Пожалуйста, оцените работу администратора Wnsuuu:", reply_markup=markup)

def show_users_page(chat_id, page=0, message_id=None):
    users_list = list(known_users.items())
    total_users = len(users_list)
    per_page = 10
    max_pages = math.ceil(total_users / per_page)
    
    if page < 0: page = 0
    elif page >= max_pages and max_pages > 0: page = max_pages - 1
    
    start = page * per_page
    end = start + per_page
    current_users = users_list[start:end]
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    text = f"👥 <b>Список пользователей (Страница {page+1}/{max_pages}):</b>\nВсего в базе: {total_users}\n\n<i>Кликните на пользователя, чтобы написать ему личное сообщение:</i>"
    
    for uid, uname in current_users:
        display_name = f"@{uname}" if uname else f"ID: {uid}"
        markup.add(types.InlineKeyboardButton(f"👤 {display_name}", callback_data=f"usermenu_{uid}"))
    
    nav_buttons = []
    if page > 0: nav_buttons.append(types.InlineKeyboardButton("⬅️ Назад", callback_data=f"userpage_{page-1}"))
    if page < max_pages - 1: nav_buttons.append(types.InlineKeyboardButton("Вперед ➡️", callback_data=f"userpage_{page+1}"))
    
    if nav_buttons: markup.row(*nav_buttons)
    markup.add(types.InlineKeyboardButton("🔙 Закрыть", callback_data="cancel_admin_action"))
    
    if message_id:
        try: bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=markup, parse_mode="HTML")
        except: pass
    else: bot.send_message(chat_id, text, reply_markup=markup, parse_mode="HTML")

def process_personal_message(message, target_id):
    if check_cancel(message): return
    try:
        bot.copy_message(target_id, message.chat.id, message.message_id)
        bot.send_message(message.chat.id, "✅ Сообщение успешно доставлено пользователю!", reply_markup=get_main_menu(message.chat.id))
    except Exception:
        bot.send_message(message.chat.id, "❌ Не удалось отправить сообщение. Возможно, чат удален.", reply_markup=get_main_menu(message.chat.id))

@bot.message_handler(commands=['start'])
def send_welcome(message):
    save_user(message.from_user, message.chat.id) 
    cleanup_media(message.chat.id)
    bot.send_message(message.chat.id, f"Здравствуйте, {message.from_user.first_name}! Добро пожаловать в нашу кондитерскую. Для выбора десерта нажмите на кнопку «🎂 Каталог»👇", reply_markup=get_main_menu(message.chat.id))

def process_broadcast_step(message):
    if check_cancel(message): return
    success, failed = 0, 0
    bot.send_message(message.chat.id, "⏳ Начинаю рассылку...", reply_markup=get_main_menu(message.chat.id))
    for user_id in known_users.keys():
        if int(user_id) in ADMINS: continue
        try:
            bot.copy_message(user_id, message.chat.id, message.message_id)
            success += 1
        except: failed += 1
    bot.send_message(message.chat.id, f"✅ <b>Рассылка завершена!</b>\n\nУспешно: {success}\nНе удалось: {failed}", parse_mode="HTML")

@bot.message_handler(func=lambda message: message.chat.id in active_support_chats, content_types=['text', 'photo', 'video', 'document', 'voice', 'sticker', 'audio'])
def handle_support_chat(message):
    if message.text == "❌ Завершить диалог":
        end_support_chat(message.chat.id)
        return
    partner_id = active_support_chats[message.chat.id]
    try: bot.copy_message(partner_id, message.chat.id, message.message_id)
    except: bot.send_message(message.chat.id, "❌ Ошибка отправки сообщения. Попробуйте еще раз.")

# === ОБРАБОТКА ТЕКСТА ===
@bot.message_handler(content_types=['text'])
def handle_text(message):
    chat_id = message.chat.id
    save_user(message.from_user, chat_id) 
    cleanup_media(chat_id)
    
    if message.text == "🔙 Отменить оформление" or message.text == "❌ Отмена": return bot.send_message(chat_id, "Вы в главном меню.", reply_markup=get_main_menu(chat_id))

    if message.text == "🎂 Каталог":
        markup = types.InlineKeyboardMarkup()
        for item_id, item_data in CATALOG.items():
            if not item_id.startswith("bakery"):
                markup.add(types.InlineKeyboardButton(f"{item_data['name']} - {item_data['price']} ₽", callback_data=f"view_{item_id}"))
        markup.add(types.InlineKeyboardButton("🥐 Посмотреть выпечку", callback_data="show_bakery"))
        bot.send_message(chat_id, "Наше меню десертов (нажмите для подробностей):", reply_markup=markup)

    elif message.text == "🛒 Корзина": show_cart(chat_id)
    elif message.text == "❓ Контакты и FAQ": bot.send_message(chat_id, "📍 **Самовывоз:** обл.Московская, г.о.Ленинский,\n п.Битца, мкр.Южная Битца, ул.Парковая, д.1\n \n⏰ **Сроки:** выбираются при заказе в боте, либо обговариваются с кондитером.\n\nПо сложным заказам пишите кондитеру.", parse_mode="Markdown")
    elif message.text == "💬 Связаться с кондитером": bot.send_message(chat_id, "👩‍🍳 <b>Связь с кондитером:</b>\n\n✈️ Telegram: @Vergunova_ira\n📞 Телефон: +79038734877\n\n<i>Пишите по любым вопросам, обсудим индивидуальный декор и начинку!</i>", parse_mode="HTML")
    elif message.text == "🆘 Проблемы с ботом? Вызовите поддержку!":
        bot.send_message(chat_id, "⏳ Заявка отправлена. Ожидайте подключения администратора...")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Принять заявку", callback_data=f"support_accept_{chat_id}"))
        username_str = f"@{message.from_user.username}" if message.from_user.username else "Без ника"
        bot.send_message(MAIN_ADMIN_ID, f"🚨 <b>ЗАПРОС В ПОДДЕРЖКУ</b>\nОт: {username_str} (ID: <code>{chat_id}</code>)", reply_markup=markup, parse_mode="HTML")
    elif message.text == "⚙️ Управление меню" and chat_id in ADMINS:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("➕ Добавить товар", callback_data="admin_add"), types.InlineKeyboardButton("🗑 Удалить товар", callback_data="admin_del"))
        markup.add(types.InlineKeyboardButton("✏️ Изменить товар", callback_data="admin_edit"))
        bot.send_message(chat_id, "🔧 <b>Панель управления меню:</b>\n*Подсказка:* Если ID начинается на `bakery`, он попадет в 'Выпечка'.", reply_markup=markup, parse_mode="Markdown")
    elif message.text == "📣 Рассылка" and chat_id in ADMINS:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("❌ Отмена"))
        msg = bot.send_message(chat_id, f"📣 <b>РЕЖИМ РАССЫЛКИ</b>\n\nВ базе <b>{len(known_users)}</b> пользователей.\nОтправьте сообщение (можно с фото) для рассылки всем клиентам.", parse_mode="HTML", reply_markup=markup)
        bot.register_next_step_handler(msg, process_broadcast_step)
    elif message.text == "🔄 Перезапуск" and chat_id in ADMINS: send_welcome(message)
    elif message.text == "👥 Админы" and chat_id == MAIN_ADMIN_ID:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("➕ Добавить админа", callback_data="add_admin"), types.InlineKeyboardButton("❌ Удалить админа", callback_data="del_admin"))
        bot.send_message(chat_id, "👑 <b>Управление администраторами:</b>", reply_markup=markup, parse_mode="HTML")
    elif message.text == "📊 Мой рейтинг" and chat_id == MAIN_ADMIN_ID:
        if admin_rating["reviews_count"] > 0: bot.send_message(chat_id, f"📊 <b>Ваш рейтинг поддержки:</b> {round(admin_rating['total_score'] / admin_rating['reviews_count'], 1)} ⭐\nВсего оценок: {admin_rating['reviews_count']}", parse_mode="HTML")
        else: bot.send_message(chat_id, "У вас пока нет оценок за поддержку. 😔")
    elif message.text == "👥 Все пользователи" and chat_id == MAIN_ADMIN_ID: show_users_page(chat_id, 0)
    elif message.text == "📋 Активные заказы" and chat_id in ADMINS:
        if not active_orders: return bot.send_message(chat_id, "В данный момент нет активных заказов в работе. ☕️")
        bot.send_message(chat_id, f"🟢 <b>Активные заказы ({len(active_orders)} шт):</b>", parse_mode="HTML")
        for order_id, order_info in active_orders.items():
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ Закрыть заказ (Выдан)", callback_data=f"closeorder_{order_id}"))
            markup.add(types.InlineKeyboardButton("💬 Связаться с клиентом", callback_data=f"contact_{order_info['client_id']}"))
            try: bot.send_message(chat_id, f"📌 <b>ЗАКАЗ:</b>\n\n{order_info['text']}", reply_markup=markup, parse_mode="HTML")
            except: pass

# === ОБРАБОТКА КНОПОК ===
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    chat_id = call.message.chat.id
    data = call.data
    save_user(call.from_user, chat_id) 

    if data == "cancel_admin_action":
        cleanup_media(chat_id)
        bot.answer_callback_query(call.id, "Действие отменено.")
        try: bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="Действие успешно отменено.")
        except:
            try: bot.delete_message(chat_id, call.message.message_id)
            except: pass
            bot.send_message(chat_id, "Действие успешно отменено.")
        return

    elif data.startswith("userpage_") and chat_id == MAIN_ADMIN_ID:
        page = int(data.split("_")[1])
        bot.answer_callback_query(call.id)
        show_users_page(chat_id, page, call.message.message_id)

    elif data.startswith("usermenu_") and chat_id == MAIN_ADMIN_ID:
        target_id = data.split("_")[1]
        bot.answer_callback_query(call.id)
        uname = known_users.get(target_id, "")
        display_name = f"@{uname}" if uname else f"ID: {target_id}"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✉️ Написать сообщение", callback_data=f"sendpm_{target_id}"), types.InlineKeyboardButton("🔙 К списку", callback_data="userpage_0"))
        try: bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=f"Действия с пользователем <b>{display_name}</b>:", reply_markup=markup, parse_mode="HTML")
        except: pass

    elif data.startswith("sendpm_") and chat_id == MAIN_ADMIN_ID:
        target_id = data.split("_")[1]
        bot.answer_callback_query(call.id)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("❌ Отмена"))
        msg = bot.send_message(chat_id, f"Напишите сообщение, которое хотите отправить этому пользователю:", reply_markup=markup)
        bot.register_next_step_handler(msg, process_personal_message, target_id)

    elif data.startswith("support_accept_") and chat_id == MAIN_ADMIN_ID:
        client_id = int(data.split("_")[2])
        if client_id in active_support_chats or MAIN_ADMIN_ID in active_support_chats: return bot.answer_callback_query(call.id, "Кто-то уже в чате.", show_alert=True)
        active_support_chats[client_id] = MAIN_ADMIN_ID
        active_support_chats[MAIN_ADMIN_ID] = client_id
        bot.answer_callback_query(call.id, "Чат начат!")
        try: bot.delete_message(chat_id, call.message.message_id)
        except: pass
        chat_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        chat_markup.add(types.KeyboardButton("❌ Завершить диалог"))
        bot.send_message(client_id, "Вашу заявку принял администратор.\nОпишите свою проблему сюда.", reply_markup=chat_markup)
        bot.send_message(MAIN_ADMIN_ID, "Вы подключились к чату с клиентом.", reply_markup=chat_markup)

    elif data.startswith("rate_"):
        score = int(data.split("_")[1])
        bot.answer_callback_query(call.id, "Спасибо за оценку!")
        try: bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=f"Вы оценили работу поддержки на {score}⭐. Спасибо!")
        except: pass
        admin_rating["total_score"] += score
        admin_rating["reviews_count"] += 1
        save_admin_rating() # СОХРАНЯЕМ В ОБЛАКО
        bot.send_message(MAIN_ADMIN_ID, f"📊 <b>Новая оценка поддержки!</b>\nКлиент оценил работу на <b>{score}⭐</b>.", parse_mode="HTML")

    elif data == "show_bakery":
        cleanup_media(chat_id) 
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup()
        for item_id, item_data in CATALOG.items():
            if item_id.startswith("bakery"): markup.add(types.InlineKeyboardButton(f"{item_data['name']} - {item_data['price']} ₽", callback_data=f"view_{item_id}"))
        markup.add(types.InlineKeyboardButton("🔙 Назад к десертам", callback_data="show_catalog"))
        try: bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="Наша свежая выпечка:", reply_markup=markup)
        except:
            try: bot.delete_message(chat_id, call.message.message_id)
            except: pass
            bot.send_message(chat_id, "Наша свежая выпечка:", reply_markup=markup)

    elif data == "show_catalog":
        cleanup_media(chat_id) 
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup()
        for item_id, item_data in CATALOG.items():
            if not item_id.startswith("bakery"): markup.add(types.InlineKeyboardButton(f"{item_data['name']} - {item_data['price']} ₽", callback_data=f"view_{item_id}"))
        markup.add(types.InlineKeyboardButton("🥐 Посмотреть выпечку", callback_data="show_bakery"))
        try: bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="Наше меню десертов:", reply_markup=markup)
        except:
            try: bot.delete_message(chat_id, call.message.message_id)
            except: pass
            bot.send_message(chat_id, "Наше меню десертов:", reply_markup=markup)

    elif data == "add_admin" and chat_id == MAIN_ADMIN_ID:
        bot.answer_callback_query(call.id)
        msg = bot.send_message(chat_id, "Введите никнейм пользователя (например: `@ivan`) или его цифровой ID.", reply_markup=get_cancel_markup())
        bot.register_next_step_handler(msg, process_add_admin)
        
    elif data == "del_admin" and chat_id == MAIN_ADMIN_ID:
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup()
        for adm in ADMINS:
            if adm == MAIN_ADMIN_ID: continue
            uname = known_users.get(str(adm), "Без ника")
            markup.add(types.InlineKeyboardButton(f"❌ Удалить: @{uname} ({adm})", callback_data=f"rm_admin_{adm}"))
        markup.add(types.InlineKeyboardButton("🔙 Отмена", callback_data="cancel_admin_action"))
        try: bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="Кого лишить прав администратора?", reply_markup=markup)
        except:
            try: bot.delete_message(chat_id, call.message.message_id)
            except: pass
            bot.send_message(chat_id, "Кого лишить прав администратора?", reply_markup=markup)
        
    elif data.startswith("rm_admin_") and chat_id == MAIN_ADMIN_ID:
        adm_to_remove = int(data.split("_")[2])
        if adm_to_remove in ADMINS:
            ADMINS.remove(adm_to_remove)
            del_admin_db(adm_to_remove) # УДАЛЯЕМ ИЗ ОБЛАКА
            try: bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="✅ Пользователь удален из админов.")
            except: pass
        else: bot.answer_callback_query(call.id, "Ошибка!")

    elif data == "admin_add" and chat_id in ADMINS:
        bot.answer_callback_query(call.id)
        msg = bot.send_message(chat_id, "📝 Введите уникальный ID товара английскими буквами.", reply_markup=get_cancel_markup())
        bot.register_next_step_handler(msg, admin_add_step1_id)
        
    elif data == "admin_del" and chat_id in ADMINS:
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup()
        for item_id, item_data in CATALOG.items(): markup.add(types.InlineKeyboardButton(f"❌ Удалить: {item_data['name']}", callback_data=f"delitem_{item_id}"))
        markup.add(types.InlineKeyboardButton("🔙 Отмена", callback_data="cancel_admin_action"))
        try: bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="Выберите товар для удаления:", reply_markup=markup)
        except: pass
        
    elif data.startswith("delitem_") and chat_id in ADMINS:
        item_id = data.split("_")[1]
        if item_id in CATALOG:
            del CATALOG[item_id]
            delete_catalog_item(item_id) # УДАЛЯЕМ ИЗ ОБЛАКА
            try: bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=f"✅ Товар удален.")
            except: pass
        else: bot.answer_callback_query(call.id, "Товар не найден!")

    elif data == "admin_edit" and chat_id in ADMINS:
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup()
        for item_id, item_data in CATALOG.items(): markup.add(types.InlineKeyboardButton(f"✏️ {item_data['name']}", callback_data=f"edititem_{item_id}"))
        markup.add(types.InlineKeyboardButton("🔙 Отмена", callback_data="cancel_admin_action"))
        try: bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="Какой товар вы хотите изменить?", reply_markup=markup)
        except: pass

    elif data.startswith("edititem_") and chat_id in ADMINS:
        item_id = data.split("_")[1]
        if item_id not in CATALOG: return bot.answer_callback_query(call.id, "Товар не найден!", show_alert=True)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📝 Название", callback_data=f"editfield_{item_id}_name"), types.InlineKeyboardButton("💰 Цена", callback_data=f"editfield_{item_id}_price"))
        markup.add(types.InlineKeyboardButton("📜 Описание", callback_data=f"editfield_{item_id}_desc"), types.InlineKeyboardButton("📸 Фото", callback_data=f"editfield_{item_id}_photo"))
        markup.add(types.InlineKeyboardButton("🔙 Отмена", callback_data="cancel_admin_action"))
        try: bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=f"Что меняем у **{CATALOG[item_id]['name']}**?", reply_markup=markup, parse_mode="Markdown")
        except: pass

    elif data.startswith("editfield_") and chat_id in ADMINS:
        parts = data.split("_")
        item_id, field = parts[1], parts[2]
        bot.answer_callback_query(call.id)
        temp_admin_items[chat_id] = {'id': item_id, 'field': field}
        if field == "photo":
            temp_admin_items[chat_id]['photos'] = []
            msg = bot.send_message(chat_id, "📸 **Отправьте новые фото** строго ПО ОДНОМУ.\nНажмите `✅ Готово`.", reply_markup=get_photo_ready_markup(), parse_mode="Markdown")
            bot.register_next_step_handler(msg, admin_edit_photo_step)
        else:
            msg = bot.send_message(chat_id, f"Введите новое значение для поля:", reply_markup=get_cancel_markup())
            bot.register_next_step_handler(msg, admin_edit_text_step)

    elif data.startswith("view_"):
        item_id = data.split("_")[1]
        if item_id not in CATALOG: return bot.answer_callback_query(call.id, "Товар не найден!", show_alert=True)
        item = CATALOG[item_id]
        try: bot.delete_message(chat_id, call.message.message_id)
        except: pass
        cleanup_media(chat_id) 
        photos = item.get('photo', [])
        if isinstance(photos, str): photos = [photos] 
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("➕ Добавить в корзину", callback_data=f"add_{item_id}"))
        if item_id.startswith("bakery"): markup.add(types.InlineKeyboardButton("🔙 Назад к выпечке", callback_data="show_bakery"))
        else: markup.add(types.InlineKeyboardButton("🔙 Назад к десертам", callback_data="show_catalog"))
        text = f"**{item['name']}**\n\n📝 Описание: {item['desc']}\n💰 Цена: {item['price']} руб."
        if not photos: bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")
        elif len(photos) == 1: 
            try: bot.send_photo(chat_id, photo=photos[0], caption=text, reply_markup=markup, parse_mode="Markdown")
            except: bot.send_message(chat_id, text + "\n*(Фото не загружено)*", reply_markup=markup, parse_mode="Markdown")
        else:
            try:
                media = [types.InputMediaPhoto(p) for p in photos[:4]] 
                msgs = bot.send_media_group(chat_id, media)
                user_last_media[chat_id] = [m.message_id for m in msgs]
                bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")
            except: bot.send_message(chat_id, text + "\n*(Фото не загружено)*", reply_markup=markup, parse_mode="Markdown")

    elif data.startswith("add_"):
        item_id = data.split("_", 1)[1] 
        if item_id not in CATALOG: return
        bot.answer_callback_query(call.id) 
        try: bot.delete_message(chat_id, call.message.message_id)
        except: pass
        cleanup_media(chat_id)
        if item_id.startswith("bakery"):
            if chat_id not in user_carts: user_carts[chat_id] = []
            user_carts[chat_id].append({'item_id': item_id, 'filling': '-', 'design': '-', 'comment': '-'})
            bot.send_message(chat_id, f"✅ **{CATALOG[item_id]['name']}** добавлено в корзину!", reply_markup=get_main_menu(chat_id), parse_mode="Markdown")
        else: show_filling_menu(chat_id, item_id)

    elif data.startswith("fill_"):
        parts = data.split("_")
        item_id, filling = parts[1], parts[2]
        bot.answer_callback_query(call.id)
        try: bot.delete_message(chat_id, call.message.message_id)
        except: pass
        ask_design(chat_id, item_id, filling)

    elif data.startswith("rmcart_"):
        idx = int(data.split("_")[1])
        if chat_id in user_carts and len(user_carts[chat_id]) > idx:
            del user_carts[chat_id][idx]
            bot.answer_callback_query(call.id, "Товар удален из корзины!")
            try: bot.delete_message(chat_id, call.message.message_id)
            except: pass
            show_cart(chat_id)

    elif data == "clear_cart":
        user_carts[chat_id] = []
        try: bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="🗑 Корзина очищена.")
        except: pass
            
    elif data == "checkout":
        if chat_id not in user_carts or not user_carts[chat_id]: return bot.answer_callback_query(call.id, text="Корзина пуста!")
        bot.answer_callback_query(call.id)
        user_orders[chat_id] = {'address': {}} 
        ask_checkout_method(chat_id, call.message.message_id)

    elif data == "cancel_checkout_inline":
        bot.answer_callback_query(call.id, "Оформление отменено.")
        if chat_id in user_orders: del user_orders[chat_id]
        try: bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="Оформление заказа прервано.")
        except: pass

    elif data == "order_pickup":
        user_orders[chat_id]['type'] = 'Самовывоз'
        ask_date(chat_id)
        
    elif data == "order_delivery":
        user_orders[chat_id]['type'] = 'Доставка'
        if 'address' not in user_orders[chat_id]: user_orders[chat_id]['address'] = {}
        try: bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="Вы выбрали доставку 🚚\n\nЗаполните данные адреса с помощью кнопок ниже:", reply_markup=get_address_markup(chat_id))
        except: pass

    elif data.startswith("addr_"):
        field = data.split("_")[1]
        if field == "done":
            if 'street' not in user_orders[chat_id].get('address', {}): return bot.answer_callback_query(call.id, text="⚠️ Сначала укажите город, улицу и дом!", show_alert=True)
            bot.answer_callback_query(call.id)
            ask_location(chat_id)
            return
        prompts = {"street": "Введите город улицу и дом:", "apt": "Введите номер квартиры:", "ent": "Введите номер подъезда:", "floor": "Введите этаж:", "com": "Напишите комментарий к адресу:"}
        bot.answer_callback_query(call.id)
        msg = bot.send_message(chat_id, prompts.get(field, "Введите данные:"), reply_markup=get_step_back_markup())
        bot.register_next_step_handler(msg, process_address_details_input, field)

    elif data == "confirm_order":
        bot.answer_callback_query(call.id, "Заказ подтвержден!")
        bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=None) 
        send_order_to_admin(chat_id, call.from_user.username) 
        
    elif data == "restart_order":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(chat_id, call.message.message_id)
        except: pass
        user_orders[chat_id] = {'address': {}}
        ask_checkout_method(chat_id)

    elif data == "edit_order":
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup(row_width=2)
        if user_orders[chat_id].get('type') == 'Доставка': markup.add(types.InlineKeyboardButton("Изменить адрес 📍", callback_data="editorder_address"))
        markup.add(types.InlineKeyboardButton("Изменить дату 📅", callback_data="editorder_date"), types.InlineKeyboardButton("Изменить время ⏰", callback_data="editorder_time"))
        markup.add(types.InlineKeyboardButton("Изменить телефон 📞", callback_data="editorder_phone"))
        markup.add(types.InlineKeyboardButton("🔙 Назад", callback_data="review_back"))
        try: bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="Что именно вы хотите исправить?", reply_markup=markup)
        except: pass

    elif data == "review_back":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(chat_id, call.message.message_id)
        except: pass
        show_order_review(chat_id) 

    elif data.startswith("editorder_"):
        field = data.split("_")[1]
        bot.answer_callback_query(call.id)
        try: bot.delete_message(chat_id, call.message.message_id)
        except: pass
        user_orders[chat_id]['is_editing'] = True 
        if field == "address": bot.send_message(chat_id, "Изменение адреса:", reply_markup=get_address_markup(chat_id))
        else:
            prompts = {"date": "Введите правильную дату:", "time": "Введите правильное время:", "phone": "Введите правильный номер телефона:"}
            msg = bot.send_message(chat_id, prompts[field], reply_markup=get_step_back_markup())
            bot.register_next_step_handler(msg, process_edit_field, field)

    elif data.startswith("accept_") and chat_id in ADMINS:
        bot.answer_callback_query(call.id, text="Заказ принят!") 
        parts = data.split("_")
        client_id, total_price = parts[1], parts[2]
        admin_markup = types.InlineKeyboardMarkup()
        admin_markup.add(types.InlineKeyboardButton("💬 Связаться с клиентом", callback_data=f"contact_{client_id}"))
        try: bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=f"{call.message.text}\n\n⏳ <b>СТАТУС: ОЖИДАЕТ ОПЛАТЫ</b>", reply_markup=admin_markup, parse_mode="HTML")
        except: pass
        client_text = f"🎉 <b>Ваш заказ принят!</b>\n\n💰 <b>Сумма к оплате:</b> {total_price} руб.\n💳 <b>Реквизиты:</b>\n<code>+79038734877</code> (СберБанк)\nПолучатель: Ирина В.\n\n📸 <b>Отправьте скриншот чека в этот чат.</b>"
        try: 
            msg = bot.send_message(client_id, client_text, parse_mode="HTML")
            bot.register_next_step_handler(msg, process_receipt_photo)
        except: pass

    elif data == "client_paid":
        bot.answer_callback_query(call.id, text="Уведомление отправлено!")
        if call.message.content_type == 'photo':
            try: bot.edit_message_caption(chat_id=chat_id, message_id=call.message.message_id, caption=f"{call.message.caption}\n\n⏳ <i>Отправлено кондитеру...</i>", parse_mode="HTML")
            except: pass
        else:
            try: bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=f"{call.message.text}\n\n⏳ <i>Отправлено кондитеру...</i>", parse_mode="HTML")
            except: pass
        
        receipt_photo = pending_receipts.get(chat_id)
        admin_text = f"💰 <b>ВНИМАНИЕ!</b>\nКлиент (ID: <code>{chat_id}</code>) оплатил заказ."
        admin_markup = types.InlineKeyboardMarkup()
        admin_markup.add(types.InlineKeyboardButton("✅ Оплата получена", callback_data=f"payment_ok_{chat_id}"), types.InlineKeyboardButton("❌ Оплата не получена", callback_data=f"payment_fail_{chat_id}"))
        admin_markup.add(types.InlineKeyboardButton("💬 Связаться с клиентом", callback_data=f"contact_{chat_id}"))
        
        for adm in ADMINS:
            try: 
                if receipt_photo: bot.send_photo(adm, photo=receipt_photo, caption=admin_text, reply_markup=admin_markup, parse_mode="HTML")
                else: bot.send_message(adm, admin_text, reply_markup=admin_markup, parse_mode="HTML")
            except: pass
        if chat_id in pending_receipts: del pending_receipts[chat_id]

    elif data.startswith("payment_ok_") and chat_id in ADMINS:
        client_id = data.split("_")[2]
        bot.answer_callback_query(call.id, text="Оплата подтверждена!")
        order_id = f"ord{int(time.time())}"
        saved_text = pending_orders_text.get(str(client_id), "Детали заказа сохранены.")
        
        active_orders[order_id] = {"client_id": client_id, "text": saved_text}
        save_active_order(order_id, client_id, saved_text) # СОХРАНЯЕМ В ОБЛАКО
        if str(client_id) in pending_orders_text: del pending_orders_text[str(client_id)]
        
        admin_markup = types.InlineKeyboardMarkup()
        admin_markup.add(types.InlineKeyboardButton("💬 Связаться с клиентом", callback_data=f"contact_{client_id}"))
        admin_text_update = f"💰 <b>ОПЛАТА ПОДТВЕРЖДЕНА</b> ✅\nЗаказ перенесен в активные!"
        try:
            if call.message.content_type == 'photo': bot.edit_message_caption(chat_id=chat_id, message_id=call.message.message_id, caption=admin_text_update, reply_markup=admin_markup, parse_mode="HTML")
            else: bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=admin_text_update, reply_markup=admin_markup, parse_mode="HTML")
        except: pass
        try: bot.send_message(client_id, "✅ <b>Оплата успешно получена!</b>\nВаш заказ передан в работу. 🧁", parse_mode="HTML")
        except: pass

    elif data.startswith("payment_fail_") and chat_id in ADMINS:
        client_id = data.split("_")[2]
        bot.answer_callback_query(call.id, text="Уведомление отправлено!")
        admin_markup = types.InlineKeyboardMarkup()
        admin_markup.add(types.InlineKeyboardButton("💬 Связаться с клиентом", callback_data=f"contact_{client_id}"))
        try:
            if call.message.content_type == 'photo': bot.edit_message_caption(chat_id=chat_id, message_id=call.message.message_id, caption="❌ ОПЛАТА НЕ НАЙДЕНА", reply_markup=admin_markup, parse_mode="HTML")
            else: bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="❌ ОПЛАТА НЕ НАЙДЕНА", reply_markup=admin_markup, parse_mode="HTML")
        except: pass
        try: bot.send_message(client_id, "⚠️ <b>Внимание!</b>\nПеревод пока не поступил. Свяжитесь с кондитером.", parse_mode="HTML")
        except: pass

    elif data.startswith("reject_") and chat_id in ADMINS:
        client_id = data.split("_")[1]
        bot.answer_callback_query(call.id, text="Заказ отклонен!") 
        admin_markup = types.InlineKeyboardMarkup()
        admin_markup.add(types.InlineKeyboardButton("💬 Связаться с клиентом", callback_data=f"contact_{client_id}"))
        try: bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=f"{call.message.text}\n\n❌ СТАТУС: ЗАКАЗ ОТКЛОНЕН", reply_markup=admin_markup)
        except: pass
        try: bot.send_message(client_id, "😔 К сожалению, кондитер не может принять ваш заказ.")
        except: pass

    elif data.startswith("contact_") and chat_id in ADMINS:
        client_id = data.split("_")[1]
        bot.answer_callback_query(call.id, "Уведомление отправлено!")
        try: bot.send_message(client_id, "👩‍🍳 <b>Внимание!</b>\nКондитер хочет связаться с вами. Напишите ей: @Vergunova_ira", parse_mode="HTML")
        except: pass

    elif data.startswith("closeorder_") and chat_id in ADMINS:
        order_id = data.split("closeorder_")[1] 
        if order_id in active_orders:
            client_id = active_orders[order_id]['client_id']
            del active_orders[order_id]
            delete_active_order(order_id) # УДАЛЯЕМ ИЗ ОБЛАКА
            bot.answer_callback_query(call.id, "Заказ закрыт!")
            current_text = call.message.text or call.message.caption or "Заказ"
            try: bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=f"{current_text}\n\n✅ СТАТУС: ЗАКАЗ ЗАКРЫТ (ВЫДАН)")
            except: pass
            try: bot.send_message(client_id, "🎉 <b>Ваш заказ выдан!</b>\nБудем рады видеть вас снова! ❤️", parse_mode="HTML")
            except: pass
        else: bot.answer_callback_query(call.id, "Заказ уже закрыт!")

def process_receipt_photo(message):
    if check_cancel(message): return
    if not message.photo and not message.document:
        msg = bot.send_message(message.chat.id, "❌ Пожалуйста, отправьте именно фото чека:")
        bot.register_next_step_handler(msg, process_receipt_photo)
        return
    photo_id = message.photo[-1].file_id if message.photo else message.document.file_id
    pending_receipts[message.chat.id] = photo_id
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💸 Я оплатил(а)", callback_data="client_paid"))
    bot.send_message(message.chat.id, "✅ Скриншот загружен! Нажмите кнопку ниже.", reply_markup=markup)

def process_add_admin(message):
    if check_cancel(message): return
    target = message.text.replace("@", "").strip().lower()
    found_id = None
    if target.isdigit(): found_id = int(target)
    else:
        for uid, uname in known_users.items():
            if uname == target:
                found_id = int(uid)
                break
    if found_id:
        if found_id not in ADMINS:
            ADMINS.append(found_id)
            add_admin_db(found_id) # СОХРАНЯЕМ В ОБЛАКО
            bot.send_message(message.chat.id, f"✅ Пользователь добавлен в администраторы!", reply_markup=get_main_menu(message.chat.id))
        else: bot.send_message(message.chat.id, "❌ Уже является админом.", reply_markup=get_main_menu(message.chat.id))
    else:
        msg = bot.send_message(message.chat.id, "❌ Пользователь не найден. Попробуйте еще раз:", reply_markup=get_cancel_markup())
        bot.register_next_step_handler(msg, process_add_admin)

def admin_add_step1_id(message):
    if check_cancel(message): return
    item_id = message.text.lower()
    if item_id in CATALOG: return bot.send_message(message.chat.id, "❌ Такой ID уже существует!", reply_markup=get_main_menu(message.chat.id))
    temp_admin_items[message.chat.id] = {'id': item_id, 'photos': []}
    msg = bot.send_message(message.chat.id, "Введите **НАЗВАНИЕ** товара:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, admin_add_step2_name)

def admin_add_step2_name(message):
    if check_cancel(message): return
    temp_admin_items[message.chat.id]['name'] = message.text
    msg = bot.send_message(message.chat.id, "Введите **ЦЕНУ** товара цифрами:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, admin_add_step3_price)

def admin_add_step3_price(message):
    if check_cancel(message): return
    try:
        temp_admin_items[message.chat.id]['price'] = int(message.text)
        msg = bot.send_message(message.chat.id, "Введите **ОПИСАНИЕ** товара:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, admin_add_step4_desc)
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ Цена должна быть числом!")
        bot.register_next_step_handler(msg, admin_add_step3_price)

def admin_add_step4_desc(message):
    if check_cancel(message): return
    temp_admin_items[message.chat.id]['desc'] = message.text
    msg = bot.send_message(message.chat.id, "📸 **Отправьте от 1 до 4 фотографий товара** ПО ОДНОЙ.\nНажмите `✅ Готово`.", reply_markup=get_photo_ready_markup(), parse_mode="Markdown")
    bot.register_next_step_handler(msg, admin_add_step5_photo)

def admin_add_step5_photo(message):
    if check_cancel(message): return
    chat_id = message.chat.id
    if message.text in ['✅ Готово', 'Готово', 'готово']:
        item_data = temp_admin_items[chat_id]
        if 'photos' not in item_data: item_data['photos'] = []
        CATALOG[item_data['id']] = {"name": item_data['name'], "price": item_data['price'], "desc": item_data['desc'], "photo": item_data['photos']}
        save_catalog_item(item_data['id'], CATALOG[item_data['id']]) # В ОБЛАКО
        bot.send_message(chat_id, f"✅ Ура! Товар **{item_data['name']}** добавлен в каталог!", reply_markup=get_main_menu(chat_id))
        del temp_admin_items[chat_id] 
        return
    if message.photo:
        temp_admin_items[chat_id]['photos'].append(message.photo[-1].file_id)
        count = len(temp_admin_items[chat_id]['photos'])
        if count >= 4:
            item_data = temp_admin_items[chat_id]
            CATALOG[item_data['id']] = {"name": item_data['name'], "price": item_data['price'], "desc": item_data['desc'], "photo": item_data['photos']}
            save_catalog_item(item_data['id'], CATALOG[item_data['id']]) # В ОБЛАКО
            bot.send_message(chat_id, f"✅ Товар **{item_data['name']}** добавлен!", reply_markup=get_main_menu(chat_id))
            del temp_admin_items[chat_id]
        else:
            msg = bot.send_message(chat_id, f"✅ Фото загружено ({count}/4). Пришлите еще или нажмите `✅ Готово`.")
            bot.register_next_step_handler(msg, admin_add_step5_photo)
    else:
        msg = bot.send_message(chat_id, "Отправьте картинку или нажмите `✅ Готово`.")
        bot.register_next_step_handler(msg, admin_add_step5_photo)

def admin_edit_text_step(message):
    if check_cancel(message): return
    chat_id = message.chat.id
    data = temp_admin_items[chat_id]
    if data['field'] == 'price':
        try: CATALOG[data['id']][data['field']] = int(message.text)
        except: 
            msg = bot.send_message(chat_id, "Цена должна быть числом!")
            return bot.register_next_step_handler(msg, admin_edit_text_step)
    else: CATALOG[data['id']][data['field']] = message.text
        
    save_catalog_item(data['id'], CATALOG[data['id']]) # В ОБЛАКО
    bot.send_message(chat_id, "✅ Изменения сохранены!", reply_markup=get_main_menu(chat_id))
    del temp_admin_items[chat_id]

def admin_edit_photo_step(message):
    if check_cancel(message): return
    chat_id = message.chat.id
    if message.text in ['✅ Готово', 'Готово', 'готово']:
        if not temp_admin_items[chat_id].get('photos'): CATALOG[temp_admin_items[chat_id]['id']]['photo'] = []
        else: CATALOG[temp_admin_items[chat_id]['id']]['photo'] = temp_admin_items[chat_id]['photos']
        save_catalog_item(temp_admin_items[chat_id]['id'], CATALOG[temp_admin_items[chat_id]['id']]) # В ОБЛАКО
        bot.send_message(chat_id, "✅ Новые фото успешно сохранены!", reply_markup=get_main_menu(chat_id))
        del temp_admin_items[chat_id]
        return
    if message.photo:
        temp_admin_items[chat_id]['photos'].append(message.photo[-1].file_id)
        count = len(temp_admin_items[chat_id]['photos'])
        if count >= 4:
            CATALOG[temp_admin_items[chat_id]['id']]['photo'] = temp_admin_items[chat_id]['photos']
            save_catalog_item(temp_admin_items[chat_id]['id'], CATALOG[temp_admin_items[chat_id]['id']]) # В ОБЛАКО
            bot.send_message(chat_id, "✅ Достигнут лимит (4 фото). Новые фото сохранены!", reply_markup=get_main_menu(chat_id))
            del temp_admin_items[chat_id]
        else:
            msg = bot.send_message(chat_id, f"✅ Фото загружено ({count}/4). Пришлите еще или нажмите `✅ Готово`.")
            bot.register_next_step_handler(msg, admin_edit_photo_step)
    else:
        msg = bot.send_message(chat_id, "Пожалуйста, отправьте картинку или нажмите `✅ Готово`.")
        bot.register_next_step_handler(msg, admin_edit_photo_step)

def show_filling_menu(chat_id, item_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("Ваниль-клубника 🍦🍓", callback_data=f"fill_{item_id}_Ваниль-клубника"))
    markup.add(types.InlineKeyboardButton("Вишня-шоколад 🍒🍫", callback_data=f"fill_{item_id}_Вишня-шоколад"))
    markup.add(types.InlineKeyboardButton("Сникерс 🥜", callback_data=f"fill_{item_id}_Сникерс"), types.InlineKeyboardButton("Красный бархат 🍒", callback_data=f"fill_{item_id}_Красный бархат"))
    markup.add(types.InlineKeyboardButton("Своя / Без начинки", callback_data=f"fill_{item_id}_Стандарт"))
    markup.add(types.InlineKeyboardButton("🔙 Назад к товару", callback_data=f"view_{item_id}"))
    bot.send_message(chat_id, f"Вы выбрали {CATALOG[item_id]['name']}.\n\n🧁 **Выберите начинку:**", reply_markup=markup, parse_mode="Markdown")

def ask_design(chat_id, item_id, filling):
    msg = bot.send_message(chat_id, f"✅ Начинка: **{filling}**\n\n🎨 **Теперь напишите в чат пожелания по дизайну:**\n*(цветовая гамма, надпись, рисунок)*", reply_markup=get_step_back_markup(["Декор не нужен"]), parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_design_step, item_id, filling)

def process_design_step(message, item_id, filling):
    if check_cancel(message): return
    if message.text == "🔙 Шаг назад к начинке":
        bot.send_message(message.chat.id, "Возвращаемся к выбору начинки...", reply_markup=types.ReplyKeyboardRemove())
        show_filling_menu(message.chat.id, item_id)
        return
    design = message.text
    if design == "Декор не нужен": design = "-"
    ask_comment(message.chat.id, item_id, filling, design)

def ask_comment(chat_id, item_id, filling, design):
    msg = bot.send_message(chat_id, "📝 **Добавьте комментарий** к этому десерту", reply_markup=get_step_back_markup(["Комментарий не нужен"]), parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_item_comment_step, item_id, filling, design)

def process_item_comment_step(message, item_id, filling, design):
    if check_cancel(message): return
    if message.text == "🔙 Шаг назад к дизайну":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("Декор не нужен"), types.KeyboardButton("🔙 Шаг назад к начинке"), types.KeyboardButton("🔙 Отменить оформление"))
        msg = bot.send_message(message.chat.id, f"✅ Начинка: **{filling}**\n\n🎨 **Теперь напишите пожелания по дизайну:**", reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_design_step, item_id, filling)
        return
    comment = message.text
    if comment == "Комментарий не нужен": comment = "-"
    chat_id = message.chat.id
    if chat_id not in user_carts: user_carts[chat_id] = []
    user_carts[chat_id].append({'item_id': item_id, 'filling': filling, 'design': design, 'comment': comment})
    bot.send_message(chat_id, f"✅ Товар успешно добавлен в корзину!", reply_markup=get_main_menu(chat_id)) 

def show_cart(chat_id):
    if chat_id not in user_carts or not user_carts[chat_id]: return bot.send_message(chat_id, "Ваша корзина пока пуста. 😔")
    items = user_carts[chat_id]
    total_price = 0
    text = "🛒 **Ваша корзина:**\n\n"
    valid_items = []
    markup = types.InlineKeyboardMarkup(row_width=5)
    delete_buttons = []
    for idx, cart_item in enumerate(items, 1):
        if cart_item['item_id'] not in CATALOG: continue 
        valid_items.append(cart_item)
        product = CATALOG[cart_item['item_id']]
        text += f"**{idx}. {product['name']}** — {product['price']} руб.\n"
        if not cart_item['item_id'].startswith("bakery"): text += f"   🍓 Начинка: {cart_item['filling']}\n   🎨 Дизайн: {cart_item['design']}\n"
        text += f"   📝 Коммент: {cart_item['comment']}\n\n"
        total_price += product['price']
        delete_buttons.append(types.InlineKeyboardButton(f"❌ {idx}", callback_data=f"rmcart_{idx-1}"))
    user_carts[chat_id] = valid_items 
    if total_price == 0: return bot.send_message(chat_id, "В корзине находятся удаленные товары. Корзина очищена.")
    text += f"💰 **Сумма за товары: {total_price} руб.**\n\n*Нажмите на номер с крестиком ниже, чтобы удалить товар из корзины:*"
    if delete_buttons: markup.add(*delete_buttons)
    markup.add(types.InlineKeyboardButton("✅ Оформить заказ", callback_data="checkout"))
    markup.add(types.InlineKeyboardButton("🗑 Очистить всё", callback_data="clear_cart"))
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

def ask_checkout_method(chat_id, message_id=None):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🚶‍♂️ Самовывоз", callback_data="order_pickup"), types.InlineKeyboardButton("🚚 Доставка", callback_data="order_delivery"))
    markup.add(types.InlineKeyboardButton("❌ Отменить оформление", callback_data="cancel_checkout_inline"))
    if message_id:
        try: bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="Выберите способ получения заказа:", reply_markup=markup)
        except: bot.send_message(chat_id, "Выберите способ получения заказа:", reply_markup=markup)
    else: bot.send_message(chat_id, "Выберите способ получения заказа:", reply_markup=markup)

def process_address_details_input(message, field):
    if check_cancel(message): return
    chat_id = message.chat.id
    if message.text == "🔙 Шаг назад":
        bot.send_message(chat_id, "Возвращаемся в меню адреса...", reply_markup=types.ReplyKeyboardRemove())
        bot.send_message(chat_id, "Анкета адреса:", reply_markup=get_address_markup(chat_id))
        return
    user_orders[chat_id]['address'][field] = message.text
    bot.send_message(chat_id, f"Сохранено! Выберите следующую деталь или нажмите '✅ АДРЕС ЗАПОЛНЕН'.", reply_markup=types.ReplyKeyboardRemove())
    bot.send_message(chat_id, "Анкета адреса:", reply_markup=get_address_markup(chat_id))

def ask_location(chat_id):
    loc_markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    loc_markup.add(types.KeyboardButton("📍 Отправить локацию", request_location=True))
    loc_markup.add(types.KeyboardButton("🔙 Шаг назад"), types.KeyboardButton("🔙 Отменить оформление"))
    msg = bot.send_message(chat_id, "Адрес сохранен! ✅\n\n**нажмите кнопку «📍 Отправить локацию» внизу экрана**.", reply_markup=loc_markup, parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_location_step)

def process_location_step(message):
    if check_cancel(message): return
    chat_id = message.chat.id
    if message.text == "🔙 Шаг назад":
        bot.send_message(message.chat.id, "Возвращаемся к анкете адреса...", reply_markup=types.ReplyKeyboardRemove())
        bot.send_message(message.chat.id, "Анкета адреса:", reply_markup=get_address_markup(message.chat.id))
        return
    if not message.location:
        msg = bot.send_message(chat_id, "Пожалуйста, используйте кнопку «📍 Отправить локацию»!")
        return bot.register_next_step_handler(msg, process_location_step)
    client_lat, client_lon = message.location.latitude, message.location.longitude
    distance = calculate_distance(SHOP_LAT, SHOP_LON, client_lat, client_lon)
    delivery_cost = BASE_DELIVERY + int(distance * PRICE_PER_KM)
    user_orders[chat_id].update({'distance': distance, 'delivery_cost': delivery_cost, 'coords': f"{client_lat},{client_lon}"})
    if user_orders[chat_id].get('is_editing'):
        user_orders[chat_id]['is_editing'] = False
        bot.send_message(chat_id, f"🗺 **Расстояние:** {distance} км\n🚚 **Доставка:** {delivery_cost} руб.\n\nАдрес обновлен!", reply_markup=get_main_menu(chat_id), parse_mode="Markdown")
        show_order_review(chat_id)
    else: ask_date(chat_id)

def ask_date(chat_id):
    if user_orders[chat_id].get('type') == 'Доставка' and not user_orders[chat_id].get('is_editing'):
        text = f"🗺 **Расстояние до вас:** {user_orders[chat_id].get('distance', 0)} км\n🚚 **Стоимость доставки:** {user_orders[chat_id].get('delivery_cost', 0)} руб.\n\nТеперь напишите **дату**, на которую нужен заказ:"
    else: text = "Напишите **дату**, на которую нужен заказ (например: 15 мая):"
    msg = bot.send_message(chat_id, text, reply_markup=get_step_back_markup(), parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_date_step)

def process_date_step(message):
    if check_cancel(message): return
    chat_id = message.chat.id
    if message.text == "🔙 Шаг назад":
        if user_orders[chat_id].get('type') == 'Доставка': ask_location(chat_id)
        else: ask_checkout_method(chat_id)
        return
    user_orders[chat_id]['date'] = message.text
    ask_time(chat_id)

def ask_time(chat_id):
    msg = bot.send_message(chat_id, "⏰ Напишите **время**, к которому нужен заказ:", reply_markup=get_step_back_markup(), parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_time_step)

def process_time_step(message):
    if check_cancel(message): return
    chat_id = message.chat.id
    if message.text == "🔙 Шаг назад":
        ask_date(chat_id)
        return
    user_orders[chat_id]['time'] = message.text
    ask_phone(chat_id)

def ask_phone(chat_id):
    msg = bot.send_message(chat_id, "📞 Оставьте свой **номер телефона** для связи:", reply_markup=get_step_back_markup(), parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_phone_step)

def process_phone_step(message):
    if check_cancel(message): return
    chat_id = message.chat.id
    if message.text == "🔙 Шаг назад":
        ask_time(chat_id)
        return
    user_orders[chat_id]['phone'] = message.text
    bot.send_message(chat_id, "Данные собраны. Переходим к проверке...", reply_markup=get_main_menu(chat_id))
    show_order_review(chat_id)

def show_order_review(chat_id):
    order = user_orders[chat_id]
    items = user_carts.get(chat_id, [])
    goods_price = sum(CATALOG[item['item_id']]['price'] for item in items if item['item_id'] in CATALOG)
    order_list = ""
    for i in items:
        if i['item_id'] not in CATALOG: continue
        order_list += f"• {CATALOG[i['item_id']]['name']} ({CATALOG[i['item_id']]['price']}₽)\n"
        if not i['item_id'].startswith("bakery"): order_list += f"  Начинка: {i['filling']}\n"
    
    total_price = goods_price
    delivery_info = ""
    address_info = ""
    if order['type'] == 'Доставка':
        total_price += order.get('delivery_cost', 0)
        delivery_info = f"🚚 **Доставка:** {order.get('delivery_cost', 0)} руб. ({order.get('distance', 0)} км)\n"
        addr = order.get('address', {})
        address_info = f"📍 **Адрес:** {addr.get('street', 'Не указан')}\n"
        address_info += "".join([f"{k}: {addr[v]}, " for k, v in [('Кв', 'apt'), ('Подъезд', 'ent'), ('Этаж', 'floor')] if v in addr])
        if 'com' in addr: address_info += f"\n📝 **Комментарий:** {addr['com']}"
        address_info += "\n"
    
    text = (
        f"📋 **ПРОВЕРЬТЕ ВАШ ЗАКАЗ:**\n\n📦 **Способ:** {order['type']}\n{address_info}"
        f"📅 **Дата:** {order['date']}\n⏰ **Время:** {order['time']}\n📞 **Телефон:** {order['phone']}\n\n"
        f"🛒 **Товары:**\n{order_list}\n{delivery_info}💰 **ИТОГО К ОПЛАТЕ: {total_price} руб.**"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Подтвердить заказ", callback_data="confirm_order"))
    markup.add(types.InlineKeyboardButton("✏️ Изменить данные", callback_data="edit_order"))
    markup.add(types.InlineKeyboardButton("🔄 Перезаполнить", callback_data="restart_order"), types.InlineKeyboardButton("❌ Отменить заказ", callback_data="cancel_checkout_inline"))
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

def process_edit_field(message, field):
    if check_cancel(message): return
    chat_id = message.chat.id
    if message.text == "🔙 Шаг назад":
        bot.send_message(chat_id, "Изменение отменено.", reply_markup=get_main_menu(chat_id))
        show_order_review(chat_id)
        return
    user_orders[chat_id][field] = message.text
    bot.send_message(chat_id, "✅ Данные обновлены!", reply_markup=get_main_menu(chat_id))
    show_order_review(chat_id)

def send_order_to_admin(chat_id, username):
    order_data = user_orders[chat_id]
    items = user_carts.get(chat_id, [])
    goods_price = sum(CATALOG[item['item_id']]['price'] for item in items if item['item_id'] in CATALOG)
    order_list = ""
    for idx, i in enumerate(items, 1):
        if i['item_id'] not in CATALOG: continue
        order_list += f"{idx}. {CATALOG[i['item_id']]['name']}\n"
        if not i['item_id'].startswith("bakery"): order_list += f"   Начинка: {i['filling']}\n   Дизайн: {i['design']}\n"
        order_list += f"   Комментарий: {i['comment']}\n"

    address_text, total_price = "", goods_price
    if order_data['type'] == 'Доставка':
        total_price += order_data.get('delivery_cost', 0)
        addr = order_data.get('address', {})
        address_text = f"📍 <b>Точный адрес:</b> {addr.get('street', 'Не указан')}\n"
        address_text += "".join([f"{k}: {addr[v]}, " for k, v in [('Кв', 'apt'), ('Подъезд', 'ent'), ('Этаж', 'floor')] if v in addr])
        if 'com' in addr: address_text += f"\n📝 <b>Комментарий:</b> {addr['com']}"
        address_text += f"\n🗺 <b>Гео-метка:</b> <a href='https://yandex.ru/maps/?pt={order_data['coords'].split(',')[1]},{order_data['coords'].split(',')[0]}&z=16'>Открыть в Яндекс</a>\n🚚 <b>Цена доставки:</b> {order_data.get('delivery_cost', 0)} руб.\n\n"

    bot.send_message(chat_id, "⏳ Ваш заказ отправлен кондитеру! Ожидайте подтверждения.")
    username_str = f"@{username}" if username else "Скрыт или отсутствует"
    admin_text = f"🚨 <b>НОВЫЙ ЗАКАЗ!</b> 🚨\n\n👤 Клиент: {username_str} (ID: <code>{chat_id}</code>)\n📞 Телефон: {order_data['phone']}\n📅 Дата: <b>{order_data['date']}</b>\n⏰ Время: <b>{order_data['time']}</b>\n\n📦 <b>Способ:</b> {order_data['type']}\n{address_text}🛒 <b>Заказ ({goods_price} руб):</b>\n{order_list}\n💰 <b>ИТОГО К ОПЛАТЕ: {total_price} руб.</b>"
    pending_orders_text[str(chat_id)] = admin_text.replace("🚨 <b>НОВЫЙ ЗАКАЗ!</b> 🚨\n\n", "")
    
    admin_markup = types.InlineKeyboardMarkup()
    admin_markup.add(types.InlineKeyboardButton("✅ Принять", callback_data=f"accept_{chat_id}_{total_price}"), types.InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{chat_id}"))
    for adm in ADMINS:
        try: bot.send_message(adm, admin_text, reply_markup=admin_markup, parse_mode="HTML")
        except: pass
    user_carts[chat_id] = [] 
    del user_orders[chat_id]

# === ЗАПУСК ===
if __name__ == "__main__":
    bot.delete_webhook()
    print("🚀 БОТ ЗАПУЩЕН! Успешно подключен к облачной базе данных Supabase.")
    bot.infinity_polling()
