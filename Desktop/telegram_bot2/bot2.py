import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from datetime import datetime

TOKEN = "8306438881:AAEFg_MpnXk_iY2zHA5cGJomFv_kVAygbLk"
ADMIN_CHAT_ID = 5612586446  # группа для отчетов и напоминаний

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- Главное меню ---
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📤 Отправить отчет")],
        [KeyboardButton(text="📌 Установить напоминание")],
        [KeyboardButton(text="✏ Редактировать напоминание")],
    ],
    resize_keyboard=True
)

# FSM
class Form(StatesGroup):
    waiting_for_name = State()
    waiting_for_report = State()
    reminder_date = State()
    reminder_time = State()
    reminder_text = State()
    editing_choice = State()
    editing_value = State()

# --- Хранилища ---
user_names = {}  # user_id -> name
reminders = []   # список кортежей (datetime, text, user_id)

# --- Inline кнопки для редактирования ---
edit_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Дата", callback_data="edit_date"),
            InlineKeyboardButton(text="Время", callback_data="edit_time"),
            InlineKeyboardButton(text="Содержание", callback_data="edit_text"),
        ]
    ]
)

# --- Старт ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer("Привет! Введи своё имя для отчетов:", reply_markup=main_kb)
    await state.set_state(Form.waiting_for_name)

@dp.message(Form.waiting_for_name, F.text)
async def process_name(message: types.Message, state: FSMContext):
    user_names[message.from_user.id] = message.text
    await message.answer(f"Спасибо, {message.text}! Теперь можешь отправлять отчёты и устанавливать напоминания.", reply_markup=main_kb)
    await state.clear()

# --- Отчёты ---
@dp.message(F.text == "📤 Отправить отчет")
async def send_report(message: types.Message, state: FSMContext):
    if message.from_user.id not in user_names:
        await message.answer("Сначала введи имя через /start")
        return
    await message.answer("Отправь отчет (текст, фото или документ):")
    await state.set_state(Form.waiting_for_report)

@dp.message(Form.waiting_for_report, F.content_type.in_({"text", "photo", "document"}))
async def forward_report(message: types.Message, state: FSMContext):
    name = user_names.get(message.from_user.id, "Пользователь")
    if message.content_type == "text":
        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"📋 Отчет от {name}:\n\n{message.text}")
    elif message.content_type == "photo":
        await bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=message.photo[-1].file_id, caption=f"📷 Фото-отчет от {name}\n{message.caption or ''}")
    elif message.content_type == "document":
        await bot.send_document(chat_id=ADMIN_CHAT_ID, document=message.document.file_id, caption=f"📄 Документ-отчет от {name}\n{message.caption or ''}")
    await message.answer("Отчет отправлен!", reply_markup=main_kb)
    await state.clear()

# --- Напоминания ---
@dp.message(F.text == "📌 Установить напоминание")
async def set_reminder(message: types.Message, state: FSMContext):
    await message.answer("Введи дату в формате YYYY-MM-DD:")
    await state.set_state(Form.reminder_date)

@dp.message(Form.reminder_date, F.text)
async def process_date(message: types.Message, state: FSMContext):
    try:
        datetime.strptime(message.text, "%Y-%m-%d")
        await state.update_data(reminder_date=message.text)
        await message.answer("Теперь введи время в формате HH:MM:")
        await state.set_state(Form.reminder_time)
    except ValueError:
        await message.answer("Неверный формат даты. Попробуй снова: YYYY-MM-DD")

@dp.message(Form.reminder_time, F.text)
async def process_time(message: types.Message, state: FSMContext):
    try:
        datetime.strptime(message.text, "%H:%M")
        await state.update_data(reminder_time=message.text)
        await message.answer("Теперь введи текст напоминания:")
        await state.set_state(Form.reminder_text)
    except ValueError:
        await message.answer("Неверный формат времени. Попробуй снова: HH:MM")

@dp.message(Form.reminder_text, F.text)
async def process_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    dt_str = f"{data['reminder_date']} {data['reminder_time']}"
    reminder_dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    text = message.text
    reminders.append((reminder_dt, text, message.from_user.id))
    await message.answer(f"Напоминание установлено на {dt_str}: {text}", reply_markup=main_kb)
    await state.clear()

# --- Редактирование напоминания ---
@dp.message(F.text == "✏ Редактировать напоминание")
async def edit_reminder(message: types.Message, state: FSMContext):
    user_rems = [r for r in reminders if r[2] == message.from_user.id]
    if not user_rems:
        await message.answer("У тебя нет сохраненных напоминаний.")
        return
    await message.answer("Выбери, что редактировать:", reply_markup=edit_kb)

@dp.callback_query(F.data.startswith("edit_"))
async def process_edit_choice(callback: types.CallbackQuery, state: FSMContext):
    choice = callback.data.split("_")[1]
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
    data = await state.get_data()
    choice = data.get("edit_choice")
    user_rems = [r for r in reminders if r[2] == message.from_user.id]
    if not user_rems:
        await message.answer("Нет напоминаний для редактирования.")
        await state.clear()
        return
    reminder = user_rems[-1]  # редактируем последнее

    try:
        if choice == "date":
            new_date = datetime.strptime(message.text, "%Y-%m-%d").date()
            reminder_dt = reminder[0]
            reminder = (datetime.combine(new_date, reminder_dt.time()), reminder[1], reminder[2])
        elif choice == "time":
            new_time = datetime.strptime(message.text, "%H:%M").time()
            reminder_dt = reminder[0]
            reminder = (datetime.combine(reminder_dt.date(), new_time), reminder[1], reminder[2])
        elif choice == "text":
            reminder = (reminder[0], message.text, reminder[2])
        reminders[-1] = reminder
        await message.answer(f"✅ Напоминание обновлено: {reminder[0].strftime('%Y-%m-%d %H:%M')} — {reminder[1]}")
    except Exception:
        await message.answer("Неверный формат. Попробуй ещё раз.")
    await state.clear()

# --- Фоновая проверка напоминаний ---
async def reminder_loop():
    while True:
        now = datetime.now()
        for r in reminders.copy():
            dt, text, user_id = r
            if now >= dt:
                await bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"Напоминание от {user_names.get(user_id,'Пользователь')}: {text}")
                reminders.remove(r)
        await asyncio.sleep(30)

# --- Запуск ---
async def main():
    asyncio.create_task(reminder_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
