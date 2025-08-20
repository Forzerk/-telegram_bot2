import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from datetime import datetime, timedelta

TOKEN = "8306438881:AAEFg_MpnXk_iY2zHA5cGJomFv_kVAygbLk"
ADMIN_CHAT_ID = 5612586446

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Главное меню
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📌 Установить напоминание")],
    ],
    resize_keyboard=True
)

# FSM
class Form(StatesGroup):
    reminder_date = State()
    reminder_time = State()
    reminder_text = State()

# --- НАПОМИНАНИЯ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer("Привет! Чтобы создать напоминание, нажми кнопку ниже.", reply_markup=main_kb)

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

    # Запускаем задачу для отправки
    async def send_later():
        now = datetime.now()
        delay = (reminder_dt - now).total_seconds()
        if delay > 0:
            await asyncio.sleep(delay)
        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"Напоминание: {text}")

    asyncio.create_task(send_later())
    await message.answer(f"Напоминание установлено на {dt_str}: {text}", reply_markup=main_kb)
    await state.clear()

# --- ЗАПУСК ---
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

