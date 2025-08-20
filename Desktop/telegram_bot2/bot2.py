import asyncio
from aiogram import Bot, Dispatcher, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
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
    editing_date = State()
    editing_time = State()
    editing_text = State()

# Хранилище
user_names = {}
reminders = []  # Каждый элемент: {user_id, datetime, text}

# --- Старт ---
@dp.message(F.text == "/start")
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer("Привет!\nПеред отправкой отчётов, пожалуйста, введи своё имя:")
    await state.set_state(Form.waiting_for_name)

@dp.message(Form.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    user_names[message.from_user.id] = message.from_user.username or message.text
    await message.answer(f"Спасибо, {user_names[message.from_user.id]}! Теперь можешь отправлять отчёты 👇", reply_markup=main_kb)
    await state.clear()

# --- Отчеты ---
@dp.message(F.text == "📤 Отправить отчет")
async def send_report(message: types.Message, state: FSMContext):
    await message.answer("Отправь отчёт в виде текста, документа или фото:")
    await state.set_state(Form.waiting_for_report)

@dp.message(Form.waiting_for_report, F.content_type.in_({"text", "photo", "document"}))
async def forward_report(message: types.Message, state: FSMContext):
    name = user_names.get(message.from_user.id, "Пользователь")
    if message.content_type == "text":
        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"Отчет от {name}:\n\n{message.text}")
    elif message.content_type == "photo":
        await bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=message.photo[-1].file_id, caption=f"Отчет от {name}:\n\n{message.caption or ''}")
    elif message.content_type == "document":
        await bot.send_document(chat_id=ADMIN_CHAT_ID, document=message.document.file_id, caption=f"Отчет от {name}:\n\n{message.caption or ''}")
    await message.answer("Отчет отправлен!", reply_markup=main_kb)
    await state.clear()

# --- Напоминания ---
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
    reminder = {
        "user_id": message.from_user.id,
        "datetime": dt,
        "text": message.text
    }
    reminders.append(reminder)

    # Кнопка редактирования
    edit_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("Редактировать", callback_data=f"edit_{len(reminders)-1}")]
    ])

    await message.answer(f"Напоминание сохранено на {dt.strftime('%Y-%m-%d %H:%M')}:\n{message.text}", reply_markup=main_kb)
    await message.answer("Хочешь отредактировать?", reply_markup=edit_kb)
    await state.clear()

# --- Редактирование напоминаний ---
@dp.callback_query(F.data.startswith("edit_"))
async def edit_reminder(query: types.CallbackQuery, state: FSMContext):
    idx = int(query.data.split("_")[1])
    await state.update_data(edit_idx=idx)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("Изменить дату", callback_data="edit_date")],
        [InlineKeyboardButton("Изменить время", callback_data="edit_time")],
        [InlineKeyboardButton("Изменить текст", callback_data="edit_text")]
    ])
    await query.message.answer("Что хочешь изменить?", reply_markup=kb)
    await query.answer()

@dp.callback_query(F.data == "edit_date")
async def edit_date(query: types.CallbackQuery, state: FSMContext):
    await query.message.answer("Введи новую дату YYYY-MM-DD:")
    await state.set_state(Form.editing_date)
    await query.answer()

@dp.callback_query(F.data == "edit_time")
async def edit_time(query: types.CallbackQuery, state: FSMContext):
    await query.message.answer("Введи новое время HH:MM:")
    await state.set_state(Form.editing_time)
    await query.answer()

@dp.callback_query(F.data == "edit_text")
async def edit_text(query: types.CallbackQuery, state: FSMContext):
    await query.message.answer("Введи новый текст напоминания:")
    await state.set_state(Form.editing_text)
    await query.answer()

@dp.message(Form.editing_date)
async def save_edited_date(message: types.Message, state: FSMContext):
    try:
        new_date = datetime.strptime(message.text, "%Y-%m-%d").date()
        data = await state.get_data()
        idx = data['edit_idx']
        old_time = reminders[idx]["datetime"].time()
        reminders[idx]["datetime"] = datetime.combine(new_date, old_time)
        await message.answer("Дата напоминания обновлена!", reply_markup=main_kb)
    except:
        await message.answer("Неверный формат даты. Попробуй снова YYYY-MM-DD.")
    await state.clear()

@dp.message(Form.editing_time)
async def save_edited_time(message: types.Message, state: FSMContext):
    try:
        new_time = datetime.strptime(message.text, "%H:%M").time()
        data = await state.get_data()
        idx = data['edit_idx']
        old_date = reminders[idx]["datetime"].date()
        reminders[idx]["datetime"] = datetime.combine(old_date, new_time)
        await message.answer("Время напоминания обновлено!", reply_markup=main_kb)
    except:
        await message.answer("Неверный формат времени. Попробуй снова HH:MM.")
    await state.clear()

@dp.message(Form.editing_text)
async def save_edited_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    idx = data['edit_idx']
    reminders[idx]["text"] = message.text
    await message.answer("Текст напоминания обновлен!", reply_markup=main_kb)
    await state.clear()

# --- Фоновая проверка напоминаний ---
async def reminder_loop():
    while True:
        now = datetime.now()
        for r in reminders.copy():
            dt, text = r["datetime"], r["text"]
            if now >= dt:
                await bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"Напоминание:\n{text}")
                reminders.remove(r)
        await asyncio.sleep(30)

async def main():
    asyncio.create_task(reminder_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

