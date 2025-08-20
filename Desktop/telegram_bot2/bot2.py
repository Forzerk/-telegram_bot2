import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from datetime import datetime, timedelta

TOKEN = "8306438881:AAEFg_MpnXk_iY2zHA5cGJomFv_kVAygbLk"
ADMIN_CHAT_ID = -4936649070  # временный тестовый чат

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Главное меню
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📤 Отправить отчет")],
        [KeyboardButton(text="📌 Установить напоминание")],
    ],
    resize_keyboard=True
)

# Клавиатура для выбора даты
date_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Сегодня"), KeyboardButton(text="Завтра")],
        [KeyboardButton(text="Другая дата")],
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

# FSM
class Form(StatesGroup):
    waiting_for_name = State()
    waiting_for_report = State()
    reminder_date = State()
    reminder_time = State()
    reminder_text = State()

reminders = []

# START
@dp.message(Command(commands=["start"]))
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer("Привет! Введи своё имя:")
    await state.set_state(Form.waiting_for_name)

@dp.message(Form.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer(f"Спасибо, {message.text}! Вот меню 👇", reply_markup=main_kb)
    await state.clear()

# 📤 Отправка отчета
@dp.message(F.text == "📤 Отправить отчет")
async def send_report(message: types.Message, state: FSMContext):
    await message.answer("Отправь отчёт (текст/фото/документ):")
    await state.set_state(Form.waiting_for_report)

@dp.message(Form.waiting_for_report, F.content_type.in_({"text", "photo", "document"}))
async def forward_report(message: types.Message, state: FSMContext):
    data = await state.get_data()
    name = data.get("name", message.from_user.full_name)

    if message.text:
        await bot.send_message(ADMIN_CHAT_ID, f"{name} прислал отчёт:\n\n{message.text}")
    elif message.photo:
        await bot.send_photo(ADMIN_CHAT_ID, message.photo[-1].file_id,
                             caption=f"{name} прислал отчёт:\n\n{message.caption}")
    elif message.document:
        await bot.send_document(ADMIN_CHAT_ID, message.document.file_id,
                                caption=f"{name} прислал отчёт:\n\n{message.caption}")

    await message.answer("✅ Отчёт отправлен!", reply_markup=main_kb)
    await state.clear()

# 📌 Установка напоминания
@dp.message(F.text == "📌 Установить напоминание")
async def set_reminder_start(message: types.Message, state: FSMContext):
    await message.answer("Выбери дату напоминания:", reply_markup=date_kb)
    await state.set_state(Form.reminder_date)

@dp.message(Form.reminder_date)
async def process_reminder_date(message: types.Message, state: FSMContext):
    if message.text == "Сегодня":
        date = datetime.now().date()
    elif message.text == "Завтра":
        date = (datetime.now() + timedelta(days=1)).date()
    else:
        await message.answer("Введи дату в формате YYYY-MM-DD:")
        return

    await state.update_data(reminder_date=date)
    await message.answer("Теперь введи время (например 14:30):", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(Form.reminder_time)

@dp.message(Form.reminder_time)
async def process_reminder_time(message: types.Message, state: FSMContext):
    try:
        time = datetime.strptime(message.text, "%H:%M").time()
        await state.update_data(reminder_time=time)
        await message.answer("Теперь введи текст напоминания:")
        await state.set_state(Form.reminder_text)
    except ValueError:
        await message.answer("Неверный формат. Введи время так: 14:30")

@dp.message(Form.reminder_text)
async def process_reminder_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    date = data["reminder_date"]
    time = data["reminder_time"]
    name = data.get("name", message.from_user.full_name)
    text = message.text

    dt = datetime.combine(date, time)
    reminders.append((dt, text, name))

    await message.answer(f"✅ Напоминание сохранено!\n{dt} — {text}", reply_markup=main_kb)
    await state.clear()

# Фоновая проверка напоминаний
async def reminder_loop():
    while True:
        now = datetime.now()
        for r in reminders.copy():
            dt, text, name = r
            if now >= dt:
                await bot.send_message(ADMIN_CHAT_ID, f"⏰ Напоминание от {name}: {text}")
                reminders.remove(r)
        await asyncio.sleep(30)

async def main():
    asyncio.create_task(reminder_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
