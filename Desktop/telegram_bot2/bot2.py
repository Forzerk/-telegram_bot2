import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = "8306438881:AAEFg_MpnXk_iY2zHA5cGJomFv_kVAygbLk"
ADMIN_CHAT_ID = 5612586446  # сюда приходят отчеты и напоминания

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- Клавиатура ---
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("📤 Отправить отчет")],
        [KeyboardButton("📌 Установить напоминание")],
        [KeyboardButton("📝 Редактировать / Удалить напоминания")]
    ],
    resize_keyboard=True
)

# --- FSM ---
class Form(StatesGroup):
    waiting_for_name = State()
    waiting_for_report = State()
    waiting_for_reminder = State()
    choosing_reminder = State()
    editing_text = State()

# --- Хранилище ---
user_data = {}
reminders = []
next_reminder_id = 1

# --- Старт ---
@dp.message(Command(commands=["start"]))
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer("Привет! Введи своё имя:")
    await state.set_state(Form.waiting_for_name)

@dp.message(Form.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    user_data[message.from_user.id] = message.text
    await message.answer(f"Спасибо, {message.text}! Теперь можешь отправлять отчёты 👇", reply_markup=main_kb)
    await state.clear()

# --- Отчеты ---
@dp.message(F.text == "📤 Отправить отчет")
async def send_report(message: types.Message, state: FSMContext):
    await message.answer("Отправь отчёт в виде текста, документа или фото:")
    await state.set_state(Form.waiting_for_report)

@dp.message(Form.waiting_for_report, F.content_type.in_({"text", "photo", "document"}))
async def forward_report(message: types.Message, state: FSMContext):
    name = user_data.get(message.from_user.id, "Пользователь")
    if message.content_type == "text":
        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"{name} прислал отчет:\n\n{message.text}")
    elif message.content_type == "photo":
        await bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=message.photo[-1].file_id, caption=f"{name} прислал отчет:\n\n{message.caption}")
    elif message.content_type == "document":
        await bot.send_document(chat_id=ADMIN_CHAT_ID, document=message.document.file_id, caption=f"{name} прислал отчет:\n\n{message.caption}")
    await message.answer("Отчет отправлен!", reply_markup=main_kb)
    await state.clear()

# --- Установка напоминания ---
@dp.message(F.text == "📌 Установить напоминание")
async def set_reminder(message: types.Message, state: FSMContext):
    await message.answer("Напиши напоминание в формате:\n`YYYY-MM-DD HH:MM Текст напоминания`")
    await state.set_state(Form.waiting_for_reminder)

@dp.message(Form.waiting_for_reminder, F.text)
async def save_reminder(message: types.Message, state: FSMContext):
    global next_reminder_id
    try:
        dt_str, text = message.text[:16], message.text[17:]
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        reminders.append({"id": next_reminder_id, "dt": dt, "text": text, "user_id": message.from_user.id})
        next_reminder_id += 1
        await message.answer(f"Напоминание сохранено: {dt_str} — {text}", reply_markup=main_kb)
        await state.clear()
    except Exception:
        await message.answer("Неверный формат. Попробуй ещё раз:\n`YYYY-MM-DD HH:MM Текст напоминания`")

# --- Редактирование / удаление ---
@dp.message(F.text == "📝 Редактировать / Удалить напоминания")
async def edit_reminders(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_reminders = [r for r in reminders if r["user_id"] == user_id]

    if not user_reminders:
        await message.answer("У тебя пока нет сохраненных напоминаний.", reply_markup=main_kb)
        return

    kb = InlineKeyboardMarkup()
    for r in user_reminders:
        kb.add(
            InlineKeyboardButton(text=f"{r['dt'].strftime('%d.%m %H:%M')} - {r['text'][:15]}...", callback_data=f"edit_{r['id']}"),
            InlineKeyboardButton(text="❌", callback_data=f"delete_{r['id']}")
        )
    await message.answer("Выбери напоминание:", reply_markup=kb)
    await state.set_state(Form.choosing_reminder)

@dp.callback_query(lambda c: c.data and c.data.startswith("edit_"))
async def callback_edit_reminder(callback: types.CallbackQuery, state: FSMContext):
    reminder_id = int(callback.data.split("_")[1])
    await state.update_data(editing_reminder_id=reminder_id)
    await callback.message.answer("Напиши новый текст напоминания:")
    await state.set_state(Form.editing_text)
    await callback.answer()

@dp.callback_query(lambda c: c.data and c.data.startswith("delete_"))
async def callback_delete_reminder(callback: types.CallbackQuery):
    reminder_id = int(callback.data.split("_")[1])
    global reminders
    reminders = [r for r in reminders if r["id"] != reminder_id]
    await callback.message.answer("✅ Напоминание удалено.")
    await callback.answer()

@dp.message(Form.editing_text)
async def save_edited_reminder(message: types.Message, state: FSMContext):
    data = await state.get_data()
    reminder_id = data.get("editing_reminder_id")
    for r in reminders:
        if r["id"] == reminder_id:
            r["text"] = message.text
            await message.answer(f"✅ Напоминание обновлено:\n{r['dt'].strftime('%d.%m.%Y %H:%M')} - {r['text']}", reply_markup=main_kb)
            break
    await state.clear()

# --- Фоновая проверка ---
async def reminder_loop():
    while True:
        now = datetime.now()
        for r in reminders.copy():
            if now >= r["dt"]:
                user_name = user_data.get(r["user_id"], "Пользователь")
                await bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"🔔 Напоминание от {user_name}: {r['text']}")
                reminders.remove(r)
        await asyncio.sleep(30)

# --- Запуск ---
async def main():
    asyncio.create_task(reminder_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
