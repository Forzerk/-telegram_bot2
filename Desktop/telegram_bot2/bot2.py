from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio
from datetime import datetime, timedelta

TOKEN = "8306438881:AAEFg_MpnXk_iY2zHA5cGJomFv_kVAygbLk"
ADMIN_CHAT_ID = 5612586446

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Клавиатура
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📤 Отправить отчет")],
        [KeyboardButton(text="📌 Установить напоминание")],
        [KeyboardButton(text="✏ Редактировать напоминание")],
        [KeyboardButton(text="❌ Удалить напоминание")],
    ],
    resize_keyboard=True
)

# FSM для напоминаний
class ReminderStates(StatesGroup):
    waiting_for_datetime = State()
    waiting_for_text = State()

# Команда /start
@dp.message(Command(commands=["start"]))
async def start_command(message: types.Message, state: FSMContext):
    await message.answer(
        "Привет!\nПеред отправкой отчётов, пожалуйста, введи своё имя:"
    )
    await state.update_data(name=None)
    await state.set_state(ReminderStates.waiting_for_text)

# Установить напоминание
@dp.message(F.text == "📌 Установить напоминание")
async def set_reminder(message: types.Message, state: FSMContext):
    await message.answer("Введите дату и время в формате 'YYYY-MM-DD HH:MM'")
    await state.set_state(ReminderStates.waiting_for_datetime)

# Получаем дату и время
@dp.message(ReminderStates.waiting_for_datetime)
async def process_datetime(message: types.Message, state: FSMContext):
    try:
        dt = datetime.strptime(message.text, "%Y-%m-%d %H:%M")
        await state.update_data(reminder_dt=dt)
        await message.answer("Введите текст напоминания:")
        await state.set_state(ReminderStates.waiting_for_text)
    except ValueError:
        await message.answer("Неверный формат. Попробуйте снова: 'YYYY-MM-DD HH:MM'")

# Получаем текст напоминания
@dp.message(ReminderStates.waiting_for_text)
async def process_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    reminder_dt = data.get("reminder_dt")
    text = message.text
    await message.answer(f"Напоминание сохранено: {reminder_dt} — {text}")

    # Создаем задачу для отправки в нужное время
    asyncio.create_task(send_reminder(reminder_dt, text))

    await state.clear()

# Функция отправки напоминания
async def send_reminder(reminder_dt: datetime, text: str):
    now = datetime.now()
    delay = (reminder_dt - now).total_seconds()
    if delay > 0:
        await asyncio.sleep(delay)
    await bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"Напоминание: {text}")

# Отправка отчета (без изменений)
@dp.message(F.text == "📤 Отправить отчет")
async def send_report(message: types.Message):
    await message.answer("Пришлите текст, фото или файл отчета, и я перешлю администратору.")

# Получение файлов, фото и текста
@dp.message(F.content_type.in_({"text", "photo", "document"}))
async def forward_to_admin(message: types.Message):
    if message.content_type == "text":
        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=message.text)
    elif message.content_type == "photo":
        await bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=message.photo[-1].file_id, caption=message.caption)
    elif message.content_type == "document":
        await bot.send_document(chat_id=ADMIN_CHAT_ID, document=message.document.file_id, caption=message.caption)
    await message.answer("Отчет отправлен!")

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

