import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta

TOKEN = "8306438881:AAEFg_MpnXk_iY2zHA5cGJomFv_kVAygbLk"
GROUP_ID = -4936649070  # тестовая группа

bot = Bot(token=TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

# FSM для имени и напоминаний
class Form(StatesGroup):
    name = State()
    reminder_date = State()
    reminder_time = State()
    reminder_text = State()

# /start
@dp.message(commands=["start"])
async def start_command(message: types.Message, state: FSMContext):
    await message.answer("Привет!\nПеред отправкой отчётов, пожалуйста, введи своё имя:")
    await state.set_state(Form.name)

# Приём имени
@dp.message(Form.name)
async def process_name(message: types.Message, state: FSMContext):
    user_name = message.text
    await state.update_data(name=user_name)

    # Клавиатура
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Отправить отчёт")],
            [KeyboardButton(text="⏰ Установить напоминание")]
        ],
        resize_keyboard=True
    )
    await message.answer(f"Спасибо, {user_name}! Теперь можешь отправлять отчёты 👇", reply_markup=keyboard)

# Обработка кнопки "Отправить отчёт"
@dp.message(lambda msg: msg.text == "📝 Отправить отчёт")
async def ask_report(message: types.Message):
    await message.answer("Отправь отчёт в виде текста, документа или фото.")

# Текстовый отчёт
@dp.message(lambda msg: msg.text not in ["📝 Отправить отчёт", "⏰ Установить напоминание"])
async def handle_report(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_name = data.get("name", "Неизвестный")

    await bot.send_message(GROUP_ID, f"📩 Отчёт от {user_name}:\n{message.text}")
    await message.answer("✅ Текст принят и отправлен.")

# Обработка кнопки "Напоминание"
@dp.message(lambda msg: msg.text == "⏰ Установить напоминание")
async def set_reminder(message: types.Message, state: FSMContext):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Сегодня"), KeyboardButton(text="Завтра")],
            [KeyboardButton(text="Другая дата")]
        ],
        resize_keyboard=True
    )
    await message.answer("Выбери дату напоминания:", reply_markup=keyboard)
    await state.set_state(Form.reminder_date)

# Дата напоминания
@dp.message(Form.reminder_date)
async def process_reminder_date(message: types.Message, state: FSMContext):
    if message.text == "Сегодня":
        date = datetime.now().date()
    elif message.text == "Завтра":
        date = (datetime.now() + timedelta(days=1)).date()
    else:
        try:
            date = datetime.strptime(message.text, "%Y-%m-%d").date()
        except ValueError:
            await message.answer("❌ Неверный формат. Введи дату так: YYYY-MM-DD")
            return

    await state.update_data(reminder_date=date)
    await message.answer("Теперь введи время (например 14:30):", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(Form.reminder_time)

# Время напоминания
@dp.message(Form.reminder_time)
async def process_reminder_time(message: types.Message, state: FSMContext):
    try:
        time = datetime.strptime(message.text, "%H:%M").time()
    except ValueError:
        await message.answer("❌ Неверный формат. Введи время так: HH:MM")
        return

    await state.update_data(reminder_time=time)
    await message.answer("Теперь введи текст напоминания:")
    await state.set_state(Form.reminder_text)

# Текст напоминания
@dp.message(Form.reminder_text)
async def process_reminder_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_name = data.get("name", "Неизвестный")
    date = data["reminder_date"]
    time = data["reminder_time"]
    text = message.text

    reminder_datetime = datetime.combine(date, time)
    scheduler.add_job(
        send_reminder,
        "date",
        run_date=reminder_datetime,
        args=[user_name, text]
    )

    await message.answer(f"✅ Напоминание сохранено: {date} {time} — {text}")
    await state.clear()

# Отправка напоминания в группу
async def send_reminder(user_name, text):
    await bot.send_message(GROUP_ID, f"⏰ Напоминание для {user_name}: {text}")

# Запуск
async def main():
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

