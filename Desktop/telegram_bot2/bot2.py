import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from datetime import datetime
import logging
import pytz

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# === ТОКЕН И ID ГРУППЫ ===
TOKEN = "8306438881:AAEFg_MpnXk_iY2zHA5cGJomFv_kVAygbLk"
ADMIN_CHAT_ID = -1002992449853  # Новый ID группы (супергруппа)

# === Часовой пояс Узбекистана ===
uzbekistan_tz = pytz.timezone("Asia/Tashkent")

# === ID АДМИНА(ов) ===
ADMINS = {5612586446}  # Только этот пользователь может управлять напоминаниями

# === БОТ И ДИСПЕТЧЕР ===
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# === КЛАВИАТУРЫ ===
# Клавиатура для обычных пользователей
basic_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📤 Отправить отчет")],
    ],
    resize_keyboard=True
)

# Клавиатура для админа (все функции)
admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📤 Отправить отчет")],
        [KeyboardButton(text="📌 Установить напоминание")],
        [KeyboardButton(text="✏ Редактировать напоминание")],
    ],
    resize_keyboard=True
)

# Клавиатура для редактирования
edit_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Дата", callback_data="edit_date"),
            InlineKeyboardButton(text="Время", callback_data="edit_time"),
            InlineKeyboardButton(text="Содержание", callback_data="edit_text"),
        ]
    ]
)

# === FSM ===
class Form(StatesGroup):
    waiting_for_name = State()
    waiting_for_report = State()
    reminder_date = State()
    reminder_time = State()
    reminder_text = State()
    editing_choice = State()
    editing_value = State()

# === ХРАНИЛИЩА ===
user_names = {}  # user_id -> name
reminders = []   # (datetime, text, user_id)

# === /start ===
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    if message.from_user.id not in user_names:
        await message.answer("Привет! Введи своё имя для отчетов:")
        await state.set_state(Form.waiting_for_name)
    else:
        kb = admin_kb if message.from_user.id in ADMINS else basic_kb
        await message.answer(f"С возвращением, {user_names[message.from_user.id]}!", reply_markup=kb)

@dp.message(Form.waiting_for_name, F.text)
async def process_name(message: types.Message, state: FSMContext):
    user_names[message.from_user.id] = message.text
    kb = admin_kb if message.from_user.id in ADMINS else basic_kb
    await message.answer(f"Спасибо, {message.text}! Теперь можешь отправлять отчёты.", reply_markup=kb)
    await state.clear()

# === ОТПРАВКА ОТЧЁТА (все могут) ===
@dp.message(F.text == "📤 Отправить отчет")
async def send_report(message: types.Message, state: FSMContext):
    if message.from_user.id not in user_names:
        await message.answer("Сначала введи имя через /start")
        return
    await message.answer("Отправь отчет (текст, фото или документ):")
    await state.set_state(Form.waiting_for_report)

@dp.message(Form.waiting_for_report)
async def forward_report(message: types.Message, state: FSMContext):
    name = user_names.get(message.from_user.id, "Пользователь")
    try:
        if message.content_type == "text":
            await bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"📋 Отчет от {name}:\n\n{message.text}")
        elif message.content_type == "photo":
            caption = f"📷 Фото-отчет от {name}\n{message.caption or ''}"
            await bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=message.photo[-1].file_id, caption=caption)
        elif message.content_type == "document":
            caption = f"📄 Документ-отчет от {name}\n{message.caption or ''}"
            await bot.send_document(chat_id=ADMIN_CHAT_ID, document=message.document.file_id, caption=caption)
        kb = admin_kb if message.from_user.id in ADMINS else basic_kb
        await message.answer("✅ Отчет отправлен!", reply_markup=kb)
    except Exception as e:
        await message.answer("❌ Не удалось отправить отчет.")
        logging.error(f"Ошибка отправки отчета: {e}")
    await state.clear()

# === УСТАНОВКА НАПОМИНАНИЯ (только админ) ===
@dp.message(F.text == "📌 Установить напоминание")
async def set_reminder(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        await message.answer("❌ У тебя нет прав на установку напоминаний.")
        return
    await message.answer("Введи дату в формате YYYY-MM-DD:")
    await state.set_state(Form.reminder_date)

@dp.message(Form.reminder_date, F.text)
async def process_date(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        await message.answer("❌ Доступ запрещён.")
        await state.clear()
        return
    try:
        datetime.strptime(message.text, "%Y-%m-%d")
        await state.update_data(reminder_date=message.text)
        await message.answer("Теперь введи время в формате HH:MM:")
        await state.set_state(Form.reminder_time)
    except ValueError:
        await message.answer("❌ Неверный формат даты. Пример: 2025-04-06")

@dp.message(Form.reminder_time, F.text)
async def process_time(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        await message.answer("❌ Доступ запрещён.")
        await state.clear()
        return
    try:
        datetime.strptime(message.text, "%H:%M")
        await state.update_data(reminder_time=message.text)
        await message.answer("Теперь введи текст напоминания:")
        await state.set_state(Form.reminder_text)
    except ValueError:
        await message.answer("❌ Неверный формат времени. Пример: 14:30")

@dp.message(Form.reminder_text, F.text)
async def process_text(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        await message.answer("❌ Доступ запрещён.")
        await state.clear()
        return
    data = await state.get_data()
    dt_str = f"{data['reminder_date']} {data['reminder_time']}"
    try:
        naive_dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        reminder_dt = uzbekistan_tz.localize(naive_dt)
        reminders.append((reminder_dt, message.text, message.from_user.id))
        await message.answer(
            f"✅ Напоминание установлено на {reminder_dt.strftime('%d.%m.%Y в %H:%M')}:\n{message.text}",
            reply_markup=admin_kb
        )
    except Exception as e:
        await message.answer("❌ Ошибка при установке напоминания.")
        logging.error(f"Ошибка: {e}")
    await state.clear()

# === РЕДАКТИРОВАНИЕ НАПОМИНАНИЯ (только админ) ===
@dp.message(F.text == "✏ Редактировать напоминание")
async def edit_reminder(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        await message.answer("❌ У тебя нет прав на редактирование напоминаний.")
        return
    user_rems = [r for r in reminders if r[2] == message.from_user.id]
    if not user_rems:
        await message.answer("У тебя нет сохранённых напоминаний.")
        return
    reminder = user_rems[-1]
    index = reminders.index(reminder)
    await state.update_data(editing_reminder_index=index)
    await message.answer("Что хочешь изменить?", reply_markup=edit_kb)

@dp.callback_query(F.data.startswith("edit_"))
async def process_edit_choice(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMINS:
        await callback.answer("❌ У тебя нет прав.")
        return
    choice = callback.data.split("_", 1)[1]
    await state.update_data(edit_choice=choice)
    if choice == "date":
        await callback.message.answer("Введи новую дату (YYYY-MM-DD):")
    elif choice == "time":
        await callback.message.answer("Введи новое время (HH:MM):")
    elif choice == "text":
        await callback.message.answer("Введи новый текст напоминания:")
    await state.set_state(Form.editing_value)

@dp.message(Form.editing_value, F.text)
async def save_edited_reminder(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        await message.answer("❌ Доступ запрещён.")
        await state.clear()
        return
    data = await state.get_data()
    choice = data.get("edit_choice")
    index = data.get("editing_reminder_index")
    if index is None or index >= len(reminders):
        await message.answer("❌ Напоминание не найдено.")
        await state.clear()
        return
    reminder = reminders[index]
    if reminder[2] != message.from_user.id:
        await message.answer("❌ Это не твоё напоминание.")
        await state.clear()
        return
    try:
        dt, text, user_id = reminder
        if choice == "date":
            new_date = datetime.strptime(message.text, "%Y-%m-%d").date()
            new_dt = uzbekistan_tz.localize(datetime.combine(new_date, dt.time()))
            reminders[index] = (new_dt, text, user_id)
        elif choice == "time":
            new_time = datetime.strptime(message.text, "%H:%M").time()
            new_dt = uzbekistan_tz.localize(datetime.combine(dt.date(), new_time))
            reminders[index] = (new_dt, text, user_id)
        elif choice == "text":
            reminders[index] = (dt, message.text, user_id)
        else:
            await message.answer("❌ Неизвестное действие.")
            await state.clear()
            return
        new_dt = reminders[index][0]
        await message.answer(
            f"✅ Обновлено: {new_dt.strftime('%d.%m.%Y в %H:%M')} — {reminders[index][1]}",
            reply_markup=admin_kb
        )
    except ValueError:
        await message.answer("❌ Неверный формат.")
    except Exception as e:
        await message.answer("❌ Ошибка.")
        logging.error(f"Ошибка: {e}")
    await state.clear()

# === ФОНОВЫЙ ЦИКЛ НАПОМИНАНИЙ (без имени) ===
async def reminder_loop():
    print("✅ Цикл напоминаний запущен (Tashkent)")
    while True:
        try:
            now = datetime.now(uzbekistan_tz)
            for reminder in reminders.copy():
                dt, text, user_id = reminder
                if now >= dt:
                    try:
                        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"⏰ {text}")
                        reminders.remove(reminder)
                        print(f"✅ Напоминание отправлено: {text}")
                    except Exception as e:
                        print(f"❌ Ошибка отправки: {e}")
        except Exception as e:
            print(f"❌ Ошибка в цикле: {e}")
        await asyncio.sleep(10)

# === ЗАПУСК ===
async def main():
    asyncio.create_task(reminder_loop())
    logging.info("Бот запущен и готов к работе...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())