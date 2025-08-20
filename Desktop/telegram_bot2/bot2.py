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
        [KeyboardButton(text="✏ Редактировать напоминание")],
        [KeyboardButton(text="❌ Удалить напоминание")],
    ],
    resize_keyboard=True
)

# FSM для имени и напоминаний
class Form(StatesGroup):
    waiting_for_name = State()
    waiting_for_report = State()
    waiting_for_reminder = State()

# Хранилище напоминаний
reminders = []

# Старт
@dp.message(Command(commands=["start"]))
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer("Привет!\nПеред отправкой отчётов, пожалуйста, введи своё имя:")
    await state.set_state(Form.waiting_for_name)

# Получение имени
@dp.message(Form.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer(f"Спасибо, {message.text}! Теперь можешь отправлять отчёты 👇", reply_markup=main_kb)
    await state.clear()  # очищаем состояние

# Отправка отчета
@dp.message(F.text == "📤 Отправить отчет")
async def send_report(message: types.Message, state: FSMContext):
    await message.answer("Отправь отчёт в виде текста, документа или фото:")
    await state.set_state(Form.waiting_for_report)

@dp.message(Form.waiting_for_report, F.content_type.in_({"text", "photo", "document"}))
async def forward_report(message: types.Message, state: FSMContext):
    data = await state.get_data()
    name = data.get("name", "Пользователь")
    if message.content_type == "text":
        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"{name} прислал отчет:\n\n{message.text}")
    elif message.content_type == "photo":
        await bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=message.photo[-1].file_id, caption=f"{name} прислал отчет:\n\n{message.caption}")
    elif message.content_type == "document":
        await bot.send_document(chat_id=ADMIN_CHAT_ID, document=message.document.file_id, caption=f"{name} прислал отчет:\n\n{message.caption}")
    await message.answer("Отчет отправлен!", reply_markup=main_kb)
    await state.clear()

# Установка напоминания
@dp.message(F.text == "📌 Установить напоминание")
async def set_reminder(message: types.Message, state: FSMContext):
    await message.answer("Напиши напоминание в формате:\n`YYYY-MM-DD HH:MM Текст напоминания`\nПример: `2025-08-20 14:30 Сделать отчет`")
    await state.set_state(Form.waiting_for_reminder)

@dp.message(Form.waiting_for_reminder, F.text)
async def save_reminder(message: types.Message, state: FSMContext):
    try:
        dt_str, text = message.text[:16], message.text[17:]
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        reminders.append((dt, text, message.from_user.full_name))
        await message.answer(f"Напоминание сохранено: {dt_str} — {text}", reply_markup=main_kb)
        await state.clear()
    except Exception:
        await message.answer("Неверный формат. Попробуй ещё раз:\n`YYYY-MM-DD HH:MM Текст напоминания`")

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
