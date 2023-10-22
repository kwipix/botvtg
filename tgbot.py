import telebot
from telebot import types
import sqlite3

bot = telebot.TeleBot("6454410605:AAFCmT21xFcVW7hV-_QEQA-OKv9aPgM6HcY")
chosen_day = None

def initialize_db():
    with sqlite3.connect('ReservationsDB.sql') as conn:
        cur = conn.cursor()
        cur.execute('CREATE TABLE IF NOT EXISTS feedbacks (id INTEGER PRIMARY KEY, user_id INTEGER, text TEXT, rating INTEGER)')
        cur.execute('CREATE TABLE IF NOT EXISTS reservations (day TEXT, tabel INTEGER, user_id INTEGER, is_booked INTEGER, PRIMARY KEY(day, tabel))')
        conn.commit()

initialize_db()

def update_db_structure():
    with sqlite3.connect('ReservationsDB.sql') as conn:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(feedbacks)")
        columns = cur.fetchall()
        column_names = [column[1] for column in columns]

        if "rating" not in column_names:
            cur.execute('ALTER TABLE feedbacks ADD COLUMN rating INTEGER')
            conn.commit()

update_db_structure()

@bot.message_handler(commands=['start'])
def start(message):
    main_menu(message)

def main_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button1 = types.KeyboardButton("Зробити бронь")
    button2 = types.KeyboardButton("Залишити відгук")
    button3 = types.KeyboardButton("Перегляд заброньованих столів")
    button4 = types.KeyboardButton("Відмінити бронь")
    button5 = types.KeyboardButton("Відгуки")
    markup.row(button1)
    markup.row(button2, button3)
    markup.row(button4, button5)
    bot.send_message(message.chat.id, f"Вітаю, {message.from_user.first_name}! Що бажаєте?", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == 'Зробити бронь')
def choose_day(message):
    send_photo_of_tables(message)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    days = ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця", "Суббота", "Неділя"]
    for i in range(0, 7, 3):
        markup.row(*days[i:i + 3])
    bot.send_message(message.chat.id, 'Виберіть день тижня', reply_markup=markup)
    bot.register_next_step_handler(message, stolik)

def send_photo_of_tables(message):
    with open("столики.jpg", 'rb') as photo:
        bot.send_photo(message.chat.id, photo)

@bot.message_handler(func=lambda message: message.text == "Залишити відгук")
def feedback(message):
    bot.send_message(message.chat.id, "Будь ласка, залиште свій відгук:")
    bot.register_next_step_handler(message, ask_for_rating)

def ask_for_rating(message):
    with sqlite3.connect('ReservationsDB.sql') as conn:
        cur = conn.cursor()
        cur.execute('CREATE TABLE IF NOT EXISTS feedbacks (id INTEGER PRIMARY KEY, user_id INTEGER, text TEXT, rating INTEGER)')
        cur.execute('INSERT INTO feedbacks(user_id, text, rating) VALUES (?, ?, 0)', (message.from_user.id, message.text))
        conn.commit()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    ratings = [types.KeyboardButton(str(i)) for i in range(1, 6)]
    markup.row(*ratings)
    bot.send_message(message.chat.id, "Як би ви оцінили заклад за 5-бальною системою?", reply_markup=markup)
    bot.register_next_step_handler(message, save_rating)


def save_rating(message):
    with sqlite3.connect('ReservationsDB.sql') as conn:
        cur = conn.cursor()
        cur.execute('UPDATE feedbacks SET rating = ? WHERE user_id = ?', (int(message.text), message.from_user.id))
        conn.commit()

    bot.send_message(message.chat.id, "Дякуємо за ваш відгук!", reply_markup=main_menu_btn())

@bot.message_handler(func=lambda message: message.text == "Відгуки")
def show_feedbacks(message):
    with sqlite3.connect('ReservationsDB.sql') as conn:
        cur = conn.cursor()
        cur.execute('SELECT text, rating FROM feedbacks')
        feedbacks = cur.fetchall()

    if not feedbacks:
        bot.send_message(message.chat.id, "Немає жодного відгука.")
    else:
        feedback_texts = [f"Відгук: {feedback[0]}, Оцінка: {feedback[1]}" for feedback in feedbacks]
        bot.send_message(message.chat.id, "\n".join(feedback_texts))

@bot.message_handler(func=lambda message: message.text == "Перегляд заброньованих столів")
def view_bookings(message):
    with sqlite3.connect('ReservationsDB.sql') as conn:
        cur = conn.cursor()
        cur.execute('SELECT day, tabel FROM reservations WHERE is_booked=1')
        bookings = cur.fetchall()

    if not bookings:
        bot.send_message(message.chat.id, "Немає заброньованих столів.")
    else:
        booking_texts = [f"День: {booking[0]}, Столик: {booking[1]}" for booking in bookings]
        bot.send_message(message.chat.id, "\n".join(booking_texts))

def stolik(message):
    global chosen_day
    chosen_day = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    tables = [types.KeyboardButton(f"№{i}") for i in range(1, 11)]
    markup.row(*tables)
    bot.send_message(message.chat.id, 'Будь ласка, виберіть номер стола, який хочете забронювати', reply_markup=markup)
    bot.register_next_step_handler(message, tabels)

def tabels(message):
    table_num = int(message.text.split('№')[1])
    if not book_table(chosen_day, table_num, message):
        choose_day(message)

def book_table(day, table, message):
    user_id = message.from_user.id
    with sqlite3.connect('ReservationsDB.sql') as conn:
        cur = conn.cursor()
        cur.execute('CREATE TABLE IF NOT EXISTS reservations (day TEXT, tabel INTEGER, user_id INTEGER, is_booked INTEGER, PRIMARY KEY(day, tabel))')
        cur.execute('SELECT is_booked FROM reservations WHERE day=? AND tabel=?', (day, table))
        result = cur.fetchone()

        if result and result[0]:
            bot.send_message(message.chat.id, f'Стіл №{table} уже заброньовано! Будь ласка, виберіть інший стіл чи день.')
            return False

        cur.execute('INSERT OR REPLACE INTO reservations(day, tabel, user_id, is_booked) VALUES (?, ?, ?, 1)', (day, table, user_id))
        conn.commit()
        bot.send_message(message.chat.id, f'Стіл №{table} успішно заброньовано!', reply_markup=main_menu_btn())
        return True

@bot.message_handler(func=lambda message: message.text == "Відмінити бронь")
def cancel_booking_step1(message):
    user_id = message.from_user.id
    with sqlite3.connect('ReservationsDB.sql') as conn:
        cur = conn.cursor()
        cur.execute('CREATE TABLE IF NOT EXISTS reservations (day TEXT, tabel INTEGER, user_id INTEGER, is_booked INTEGER, PRIMARY KEY(day, tabel))')
        cur.execute('SELECT day, tabel FROM reservations WHERE user_id=? AND is_booked=1', (user_id,))
        bookings = cur.fetchall()

    if not bookings:
        bot.send_message(message.chat.id, 'У вас немає активних бронювань.')
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for booking in bookings:
        markup.row(types.KeyboardButton(f"{booking[0]} - №{booking[1]}"))
    markup.row(types.KeyboardButton("Назад"))
    bot.send_message(message.chat.id, 'Будь ласка, виберіть бронювання для скасування', reply_markup=markup)
    bot.register_next_step_handler(message, cancel_booking_step2)

def cancel_booking_step2(message):
    if message.text == "Назад":
        main_menu(message)
        return

    day, table_num = message.text.split(' - ')
    table = int(table_num.split('№')[1])
    with sqlite3.connect('ReservationsDB.sql') as conn:
        cur = conn.cursor()
        cur.execute('UPDATE reservations SET is_booked=0 WHERE day=? AND tabel=?', (day, table))
        conn.commit()

    bot.send_message(message.chat.id, f'Бронювання на {day} для стола №{table} було скасовано!')

def main_menu_btn():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("Головне меню"))
    return markup

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    main_menu(message)



bot.polling(none_stop=True)