import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from datetime import datetime, timedelta

TOKEN = "8306438881:AAEFg_MpnXk_iY2zHA5cGJomFv_kVAygbLk"
ADMIN_CHAT_ID = -4936649070  # Группа для отчетов и напоминаний

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Главное меню
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📤 Отправить отчет")],
        [KeyboardButton(text="📌 Установить напоминание")],
        [KeyboardButton(text="✏ Редактировать напоминание")],
        [KeyboardButton(text="❌ Удалить напоминание")],
    ],
    resize_keyboard=True
)

# Клавиатура для редактирования напоминания
edit_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Дата"), KeyboardButton(text="Время")],
        [KeyboardButton(text="Содержание")],
        [KeyboardButton(text="Назад")],
    ],
    resize_keyboard=True
)

# FSM
class Form(StatesGroup):
    waiting_for_name = State()
    waiting_for_report = State()
    waiting_for_reminder_date = State()
    waiting_for_reminder_time = State()
    waiting_for_reminder_text = State()
    waiting_for_edit_choice = State()
    waiting_for_edit_value = State()

# Временное хранилище напоминания
current_reminder = {}

# /start
@dp.message(Command(commands=["start"]))
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer("Привет!\nПеред отправкой отчётов, пожалуйста, введи своё имя:")
    await state.set_state(Form.waiting_for_name)

# Получение имени
@dp.message(Form.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer(f"Спасибо, {message.text}! Теперь можешь отправлять отчёты 👇", reply_markup=main_kb)
    await state.clear()

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
        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"От {name}:\n\n{message.text}")
    elif message.content_type == "photo":
        await bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=message.photo[-1].file_id,
                             caption=f"От {name}:\n\n{message.caption or ''}")
    elif message.content_type == "document":
        await bot.send_document(chat_id=ADMIN_CHAT_ID, document=message.document.file_id,
                                caption=f"От {name}:\n\n{message.caption or ''}")
    await message.answer("Отчет отправлен!", reply_markup=main_kb)
    await state.clear()

# Установка напоминания
@dp.message(F.text == "📌 Установить напоминание")
async def set_reminder_date(message: types.Message, state: FSMContext):
    await message.answer("Введи дату напоминания в формате YYYY-MM-DD:")
    await state.set_state(Form.waiting_for_reminder_date)

@dp.message(Form.waiting_for_reminder_date)
async def set_reminder_time(message: types.Message, state: FSMContext):
    try:
        date = datetime.strptime(message.text, "%Y-%m-%d").date()
        current_reminder['date'] = date
        await message.answer("Теперь введи время напоминания в формате HH:MM:")
        await state.set_state(Form.waiting_for_reminder_time)
    except ValueError:
        await message.answer("Неверный формат даты. Попробуй ещё раз: YYYY-MM-DD")

@dp.message(Form.waiting_for_reminder_time)
async def set_reminder_text(message: types.Message, state: FSMContext):
    try:
        time = datetime.strptime(message.text, "%H:%M").time()
        current_reminder['time'] = time
        await message.answer("Введи текст напоминания:")
        await state.set_state(Form.waiting_for_reminder_text)
    except ValueError:
        await message.answer("Неверный формат времени. Попробуй ещё раз: HH:MM")

@dp.message(Form.waiting_for_reminder_text)
async def save_reminder(message: types.Message, state: FSMContext):
    current_reminder['text'] = message.text
    data = await state.get_data()
    name = data.get("name", "Пользователь")
    dt = datetime.combine(current_reminder['date'], current_reminder['time'])
    asyncio.create_task(reminder_task(dt, name, current_reminder['text']))
    await message.answer(f"Напоминание установлено на {dt} с текстом:\n{message.text}", reply_markup=main_kb)
    await state.clear()

# Фоновая задача отправки напоминания
async def reminder_task(dt, name, text):
    now = datetime.now()
    delay = (dt - now).total_seconds()
    if delay > 0:
        await asyncio.sleep(delay)
    await bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"От {name} (напоминание): {text}")

# Редактирование напоминания
@dp.message(F.text == "✏ Редактировать напоминание")
async def edit_reminder(message: types.Message, state: FSMContext):
    if not current_reminder:
        await message.answer("Сначала установи напоминание!", reply_markup=main_kb)
        return
    await message.answer("Выбери, что хочешь изменить:", reply_markup=edit_kb)
    await state.set_state(Form.waiting_for_edit_choice)

@dp.message(Form.waiting_for_edit_choice)
async def edit_choice(message: types.Message, state: FSMContext):
    if message.text not in ["Дата", "Время", "Содержание", "Назад"]:
        await message.answer("Выбери один из вариантов на кнопках")
        return
    if message.text == "Назад":
        await message.answer("Возврат в меню", reply_markup=main_kb)
        await state.clear()
        return
    await state.update_data(edit_field=message.text)
    await message.answer(f"Введи новое значение для {message.text}:")
    await state.set_state(Form.waiting_for_edit_value)

@dp.message(Form.waiting_for_edit_value)
async def edit_value(message: types.Message, state: FSMContext):
    data = await state.get_data()
    field = data.get("edit_field")
    try:
        if field == "Дата":
            current_reminder['date'] = datetime.strptime(message.text, "%Y-%m-%d").date()
        elif field == "Время":
            current_reminder['time'] = datetime.strptime(message.text, "%H:%M").time()
        elif field == "Содержание":
            current_reminder['text'] = message.text
        await message.answer(f"{field} изменено!", reply_markup=main_kb)
    except ValueError:
        await message.answer("Неверный формат. Попробуй снова.")
    await state.clear()

# Удаление напоминания
@dp.message(F.text == "❌ Удалить напоминание")
async def delete_reminder(message: types.Message):
    current_reminder.clear()
    await message.answer("Напоминание удалено!", reply_markup=main_kb)

# Запуск
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
