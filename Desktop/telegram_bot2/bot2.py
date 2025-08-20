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
    waiting_for_reminder_date = State()
    waiting_for_reminder_time = State()
    waiting_for_reminder_text = State()
    waiting_for_edit_choice = State()
    waiting_for_new_value = State()

# Хранилище текущего напоминания пользователя (в памяти, не сохраняется)
current_reminder = {}

# Список пользователей, которым разрешено ставить напоминания
allowed_users = ["Камрон", "Иван"]  # <-- сюда добавь избранных

# Старт
@dp.message(Command())
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
        await bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=message.photo[-1].file_id, caption=f"От {name}:\n\n{message.caption or ''}")
    elif message.content_type == "document":
        await bot.send_document(chat_id=ADMIN_CHAT_ID, document=message.document.file_id, caption=f"От {name}:\n\n{message.caption or ''}")
    await message.answer("Отчет отправлен!", reply_markup=main_kb)
    await state.clear()

# Установка напоминания
@dp.message(F.text == "📌 Установить напоминание")
async def set_reminder(message: types.Message, state: FSMContext):
    data = await state.get_data()
    name = data.get("name", "")
    if name not in allowed_users:
        await message.answer("Извините, вы не можете ставить напоминания.")
        return
    await message.answer("Введите дату напоминания в формате YYYY-MM-DD:")
    await state.set_state(Form.waiting_for_reminder_date)

@dp.message(Form.waiting_for_reminder_date)
async def reminder_date(message: types.Message, state: FSMContext):
    try:
        dt = datetime.strptime(message.text, "%Y-%m-%d")
        current_reminder[message.from_user.id] = {"date": dt}
        await message.answer("Теперь введите время в формате HH:MM:")
        await state.set_state(Form.waiting_for_reminder_time)
    except:
        await message.answer("Неверный формат даты. Попробуйте снова.")

@dp.message(Form.waiting_for_reminder_time)
async def reminder_time(message: types.Message, state: FSMContext):
    try:
        t = datetime.strptime(message.text, "%H:%M").time()
        current_reminder[message.from_user.id]["time"] = t
        await message.answer("Введите текст напоминания:")
        await state.set_state(Form.waiting_for_reminder_text)
    except:
        await message.answer("Неверный формат времени. Попробуйте снова.")

@dp.message(Form.waiting_for_reminder_text)
async def reminder_text(message: types.Message, state: FSMContext):
    current_reminder[message.from_user.id]["text"] = message.text
    dt = current_reminder[message.from_user.id]["date"]
    t = current_reminder[message.from_user.id]["time"]
    text = current_reminder[message.from_user.id]["text"]
    full_dt = datetime.combine(dt, t)
    await message.answer(f"Напоминание сохранено: {full_dt} — {text}", reply_markup=main_kb)
    await state.clear()

# Фоновая задача для отправки напоминаний
async def reminder_loop():
    while True:
        now = datetime.now()
        for user_id, rem in list(current_reminder.items()):
            full_dt = datetime.combine(rem["date"], rem["time"])
            if now >= full_dt:
                data = await dp.current_state(chat=user_id).get_data()
                name = data.get("name", "Пользователь")
                await bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"Напоминание от {name}: {rem['text']}")
                current_reminder.pop(user_id)
        await asyncio.sleep(30)

# Запуск бота
async def main():
    asyncio.create_task(reminder_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
