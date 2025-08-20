import asyncio
from aiogram import Bot, Dispatcher, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from datetime import datetime

TOKEN = "8306438881:AAEFg_MpnXk_iY2zHA5cGJomFv_kVAygbLk"
ADMIN_CHAT_ID = 5612586446

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Клавиатура
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📤 Отправить отчет")],
        [KeyboardButton(text="📌 Установить напоминание")]
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

# Хранилище
reminders = []

# Старт
@dp.message(F.text == "/start")
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer("Привет! Теперь можешь отправлять отчёты 👇", reply_markup=main_kb)
    await state.clear()

# Отправка отчета
@dp.message(F.text == "📤 Отправить отчет")
async def send_report(message: types.Message, state: FSMContext):
    await message.answer("Отправь отчёт в виде текста, документа или фото:")
    await state.set_state(Form.waiting_for_report)

@dp.message(Form.waiting_for_report, F.content_type.in_({"text", "photo", "document"}))
async def forward_report(message: types.Message, state: FSMContext):
    # Используем username Telegram, если нет — "Пользователь"
    user_name = message.from_user.username or f"{message.from_user.first_name}"
    
    if message.content_type == "text":
        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"Отчет от {user_name}:\n\n{message.text}")
    elif message.content_type == "photo":
        await bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=message.photo[-1].file_id, caption=f"Отчет от {user_name}:\n\n{message.caption or ''}")
    elif message.content_type == "document":
        await bot.send_document(chat_id=ADMIN_CHAT_ID, document=message.document.file_id, caption=f"Отчет от {user_name}:\n\n{message.caption or ''}")
    
    await message.answer("Отчет отправлен!", reply_markup=main_kb)
    await state.clear()

# Напоминания
@dp.message(F.text == "📌 Установить напоминание")
async def set_reminder_date(message: types.Message, state: FSMContext):
    await message.answer("Введи дату напоминания в формате YYYY-MM-DD:")
    await state.set_state(Form.waiting_for_reminder_date)

@dp.message(Form.waiting_for_reminder_date)
async def set_reminder_time(message: types.Message, state: FSMContext):
    try:
        date = datetime.strptime(message.text, "%Y-%m-%d").date()
        await state.update_data(reminder_date=date)
        await message.answer("Введи время напоминания в формате HH:MM:")
        await state.set_state(Form.waiting_for_reminder_time)
    except:
        await message.answer("Неверный формат даты. Попробуй снова YYYY-MM-DD.")

@dp.message(Form.waiting_for_reminder_time)
async def set_reminder_text(message: types.Message, state: FSMContext):
    try:
        time = datetime.strptime(message.text, "%H:%M").time()
        await state.update_data(reminder_time=time)
        await message.answer("Напиши текст напоминания:")
        await state.set_state(Form.waiting_for_reminder_text)
    except:
        await message.answer("Неверный формат времени. Попробуй снова HH:MM.")

@dp.message(Form.waiting_for_reminder_text)
async def save_reminder(message: types.Message, state: FSMContext):
    data = await state.get_data()
    dt = datetime.combine(data['reminder_date'], data['reminder_time'])
    reminders.append((dt, message.text))
    await message.answer(f"Напоминание сохранено на {dt.strftime('%Y-%m-%d %H:%M')}:\n{message.text}", reply_markup=main_kb)
    await state.clear()

# Фоновая проверка напоминаний
async def reminder_loop():
    while True:
        now = datetime.now()
        for r in reminders.copy():
            dt, text = r
            if now >= dt:
                await bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"Напоминание:\n{text}")
                reminders.remove(r)
        await asyncio.sleep(30)

async def main():
    asyncio.create_task(reminder_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
