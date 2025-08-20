import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from datetime import datetime, date, time

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
    waiting_for_reminder_date = State()
    waiting_for_reminder_time = State()
    waiting_for_reminder_text = State()
    editing_choice = State()
    editing_value = State()

# Хранилище напоминаний: {user_id: {"date": date, "time": time, "text": str, "name": str}}
current_reminder = {}

# Список пользователей, которые могут ставить напоминания
ALLOWED_USERS = [123456789, 987654321]  # вставь реальные Telegram ID

# --- Старт и имя ---
@dp.message(Command(commands=["start"]))
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer("Привет!\nПеред отправкой отчётов, пожалуйста, введи своё имя:")
    await state.set_state(Form.waiting_for_name)

@dp.message(Form.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer(f"Спасибо, {message.text}! Теперь можешь отправлять отчёты 👇", reply_markup=main_kb)
    await state.clear()

# --- Отправка отчета ---
@dp.message(F.text == "📤 Отправить отчет")
async def send_report(message: types.Message, state: FSMContext):
    await message.answer("Отправь отчёт в виде текста, документа или фото:")
    await state.set_state(Form.waiting_for_report)

@dp.message(Form.waiting_for_report, F.content_type.in_({"text", "photo", "document"}))
async def forward_report(message: types.Message, state: FSMContext):
    data = await state.get_data()
    name = data.get("name", "Пользователь")
    if message.content_type == "text":
        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"От: {name}\n\n{message.text}")
    elif message.content_type == "photo":
        await bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=message.photo[-1].file_id,
                             caption=f"От: {name}\n\n{message.caption or ''}")
    elif message.content_type == "document":
        await bot.send_document(chat_id=ADMIN_CHAT_ID, document=message.document.file_id,
                                caption=f"От: {name}\n\n{message.caption or ''}")
    await message.answer("Отчет отправлен!", reply_markup=main_kb)
    await state.clear()

# --- Установка напоминания ---
@dp.message(F.text == "📌 Установить напоминание")
async def set_reminder(message: types.Message, state: FSMContext):
    if message.from_user.id not in ALLOWED_USERS:
        await message.answer("Извините, вы не можете ставить напоминания.")
        return
    await message.answer("Введи дату в формате YYYY-MM-DD:")
    await state.set_state(Form.waiting_for_reminder_date)

@dp.message(Form.waiting_for_reminder_date)
async def reminder_date(message: types.Message, state: FSMContext):
    try:
        dt = datetime.strptime(message.text, "%Y-%m-%d").date()
        current_reminder[message.from_user.id] = {"date": dt, "time": None, "text": None, "name": (await state.get_data()).get("name", "Пользователь")}
        await message.answer("Введи время в формате HH:MM:")
        await state.set_state(Form.waiting_for_reminder_time)
    except Exception:
        await message.answer("Неверный формат даты. Попробуй ещё раз (YYYY-MM-DD):")

@dp.message(Form.waiting_for_reminder_time)
async def reminder_time(message: types.Message, state: FSMContext):
    try:
        t = datetime.strptime(message.text, "%H:%M").time()
        current_reminder[message.from_user.id]["time"] = t
        await message.answer("Введи текст напоминания:")
        await state.set_state(Form.waiting_for_reminder_text)
    except Exception:
        await message.answer("Неверный формат времени. Попробуй ещё раз (HH:MM):")

@dp.message(Form.waiting_for_reminder_text)
async def reminder_text(message: types.Message, state: FSMContext):
    current_reminder[message.from_user.id]["text"] = message.text
    rem = current_reminder[message.from_user.id]
    full_dt = datetime.combine(rem["date"], rem["time"])
    await message.answer(f"Напоминание сохранено: {full_dt} — {rem['text']}", reply_markup=main_kb)
    await state.clear()

# --- Редактирование напоминания ---
edit_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Изменить дату"), KeyboardButton(text="Изменить время"), KeyboardButton(text="Изменить содержание")],
        [KeyboardButton(text="Отмена")]
    ],
    resize_keyboard=True
)

@dp.message(F.text == "✏ Редактировать напоминание")
async def edit_reminder(message: types.Message, state: FSMContext):
    if message.from_user.id not in current_reminder:
        await message.answer("У вас нет активного напоминания.")
        return
    await message.answer("Выберите, что хотите изменить:", reply_markup=edit_kb)
    await state.set_state(Form.editing_choice)

@dp.message(Form.editing_choice)
async def choose_edit(message: types.Message, state: FSMContext):
    text = message.text
    if text == "Отмена":
        await message.answer("Редактирование отменено.", reply_markup=main_kb)
        await state.clear()
        return
    await state.update_data(edit_field=text)
    await message.answer(f"Введите новое значение для {text}:")
    await state.set_state(Form.editing_value)

@dp.message(Form.editing_value)
async def apply_edit(message: types.Message, state: FSMContext):
    field = (await state.get_data()).get("edit_field")
    rem = current_reminder[message.from_user.id]
    try:
        if field == "Изменить дату":
            rem["date"] = datetime.strptime(message.text, "%Y-%m-%d").date()
        elif field == "Изменить время":
            rem["time"] = datetime.strptime(message.text, "%H:%M").time()
        elif field == "Изменить содержание":
            rem["text"] = message.text
        await message.answer("Напоминание обновлено.", reply_markup=main_kb)
    except Exception:
        await message.answer("Неверный формат. Попробуйте снова.")
    await state.clear()

# --- Удаление напоминания ---
@dp.message(F.text == "❌ Удалить напоминание")
async def delete_reminder(message: types.Message):
    if message.from_user.id in current_reminder:
        current_reminder.pop(message.from_user.id)
        await message.answer("Напоминание удалено.", reply_markup=main_kb)
    else:
        await message.answer("У вас нет активного напоминания.", reply_markup=main_kb)

# --- Фоновая задача для отправки напоминаний ---
async def reminder_loop():
    while True:
        now = datetime.now()
        for user_id, rem in list(current_reminder.items()):
            full_dt = datetime.combine(rem["date"], rem["time"])
            if now >= full_dt:
                await bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"Напоминание от {rem['name']}: {rem['text']}")
                current_reminder.pop(user_id)
        await asyncio.sleep(30)

# --- Запуск бота ---
async def main():
    asyncio.create_task(reminder_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

