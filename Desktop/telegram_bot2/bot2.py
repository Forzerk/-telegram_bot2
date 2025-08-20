import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from datetime import datetime, timedelta

TOKEN = "8306438881:AAEFg_MpnXk_iY2zHA5cGJomFv_kVAygbLk"
ADMIN_CHAT_ID = 5612586446  # Группа для отчетов и напоминаний

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Клавиатура
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📤 Отправить отчет")],
        [KeyboardButton(text="📌 Установить напоминание")],
    ],
    resize_keyboard=True
)

# FSM для имени и напоминаний
class Form(StatesGroup):
    waiting_for_name = State()
    waiting_for_report = State()
    waiting_for_reminder_date = State()
    waiting_for_reminder_time = State()
    waiting_for_reminder_text = State()

# Хранилище имен пользователей
user_names = {}

# Хранилище напоминаний
reminders = []

# Старт
@dp.message(Command(commands=["start"]))
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id in user_names:
        await message.answer("Ты уже ввёл имя. Можешь отправлять отчёты 👇", reply_markup=main_kb)
    else:
        await message.answer("Привет!\nПеред отправкой отчётов, пожалуйста, введи своё имя:")
        await state.set_state(Form.waiting_for_name)

# Получение имени
@dp.message(Form.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    user_names[message.from_user.id] = message.text.strip()
    await message.answer(f"Спасибо, {message.text}! Теперь можешь отправлять отчёты 👇", reply_markup=main_kb)
    await state.clear()

# Отправка отчета
@dp.message(F.text == "📤 Отправить отчет")
async def send_report(message: types.Message, state: FSMContext):
    await message.answer("Отправь отчёт в виде текста, документа или фото:")
    await state.set_state(Form.waiting_for_report)

@dp.message(Form.waiting_for_report, F.content_type.in_({"text", "photo", "document"}))
async def forward_report(message: types.Message, state: FSMContext):
    name = user_names.get(message.from_user.id, "Пользователь")
    if message.content_type == "text":
        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"От {name}:\n\n{message.text}")
    elif message.content_type == "photo":
        await bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=message.photo[-1].file_id,
                             caption=f"От {name}:\n\n{message.caption or ''}")
    elif message.content_type == "document":
        await bot.send_document(chat_id=ADMIN_CHAT_ID, document=message.document.file_id,
                                caption=f"От {name}:\n\n{message.caption or ''}")
    await message.answer("Отчет отправлен!", reply_markup=main_kb)
    await state.clear()

# Установка напоминания (дата)
@dp.message(F.text == "📌 Установить напоминание")
async def reminder_date(message: types.Message, state: FSMContext):
    await message.answer("Введи дату напоминания в формате YYYY-MM-DD:")
    await state.set_state(Form.waiting_for_reminder_date)

@dp.message(Form.waiting_for_reminder_date)
async def reminder_time(message: types.Message, state: FSMContext):
    await state.update_data(reminder_date=message.text.strip())
    await message.answer("Введи время напоминания в формате HH:MM:")
    await state.set_state(Form.waiting_for_reminder_time)

@dp.message(Form.waiting_for_reminder_time)
async def reminder_text(message: types.Message, state: FSMContext):
    await state.update_data(reminder_time=message.text.strip())
    await message.answer("Введи текст напоминания:")
    await state.set_state(Form.waiting_for_reminder_text)

@dp.message(Form.waiting_for_reminder_text)
async def save_reminder(message: types.Message, state: FSMContext):
    data = await state.get_data()
    dt_str = f"{data['reminder_date']} {data['reminder_time']}"
    text = message.text.strip()
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        reminders.append((dt, text, user_names.get(message.from_user.id, "Пользователь")))
        await message.answer(f"Напоминание сохранено: {dt_str} — {text}", reply_markup=main_kb)
        await state.clear()
    except Exception:
        await message.answer("Неверный формат даты или времени. Попробуй ещё раз:")

# Фоновая задача для отправки напоминаний
async def reminder_loop():
    while True:
        now = datetime.now()
        for r in reminders.copy():
            dt, text, name = r
            if now >= dt:
                await bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"Напоминание от {name}: {text}")
                reminders.remove(r)
        await asyncio.sleep(30)

# Запуск бота
async def main():
    asyncio.create_task(reminder_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
