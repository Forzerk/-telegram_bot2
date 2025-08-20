import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from datetime import datetime, timedelta
import pytz
import logging

# --- Логирование ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Токен и группа ---
TOKEN = "8306438881:AAEFg_MpnXk_iY2zHA5cGJomFv_kVAygbLk"
ADMIN_CHAT_ID = 5612586446  # Группа для отчетов и напоминаний

# --- Часовой пояс ---
UZBEK_TZ = pytz.timezone('Asia/Tashkent')

# --- Инициализация бота ---
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- Клавиатура ---
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📤 Отправить отчет")],
        [KeyboardButton(text="📌 Установить напоминание")],
        [KeyboardButton(text="✏ Редактировать напоминание")],
        [KeyboardButton(text="❌ Удалить напоминание")]
    ],
    resize_keyboard=True
)

# --- FSM ---
class Form(StatesGroup):
    waiting_for_name = State()
    waiting_for_report = State()
    waiting_for_reminder_text = State()
    waiting_for_reminder_datetime = State()
    editing_reminder_id = State()
    editing_reminder_text = State()

# --- Хранилище ---
user_data = {}  # id -> name
reminders = []  # {"id", "user_id", "datetime", "text"}
next_reminder_id = 1

# --- Старт ---
@dp.message(Command(commands=["start"]))
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer("Привет! Введи своё имя для начала работы с ботом:")
    await state.set_state(Form.waiting_for_name)

@dp.message(Form.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    user_data[message.from_user.id] = message.text.strip()
    await message.answer(f"Спасибо, {message.text}! Теперь можешь отправлять отчёты 👇", reply_markup=main_kb)
    await state.clear()

# --- Отчеты ---
@dp.message(F.text == "📤 Отправить отчет")
async def send_report(message: types.Message, state: FSMContext):
    await message.answer("Отправь отчёт (текст, фото или документ):")
    await state.set_state(Form.waiting_for_report)

@dp.message(Form.waiting_for_report, F.content_type.in_({"text", "photo", "document"}))
async def forward_report(message: types.Message, state: FSMContext):
    name = user_data.get(message.from_user.id, "Пользователь")
    try:
        if message.content_type == "text":
            await bot.send_message(ADMIN_CHAT_ID, f"📋 Отчет от {name}:\n\n{message.text}")
        elif message.content_type == "photo":
            caption = f"📷 Фото-отчет от {name}"
            if message.caption:
                caption += f"\n\n{message.caption}"
            await bot.send_photo(ADMIN_CHAT_ID, message.photo[-1].file_id, caption=caption)
        elif message.content_type == "document":
            caption = f"📄 Документ-отчет от {name}"
            if message.caption:
                caption += f"\n\n{message.caption}"
            await bot.send_document(ADMIN_CHAT_ID, message.document.file_id, caption=caption)
        await message.answer("✅ Отчет отправлен!", reply_markup=main_kb)
    except Exception as e:
        logger.error(f"Ошибка отправки отчета: {e}")
        await message.answer("❌ Ошибка при отправке отчета.")
    await state.clear()

# --- Установка напоминания ---
@dp.message(F.text == "📌 Установить напоминание")
async def set_reminder(message: types.Message, state: FSMContext):
    await message.answer("Напиши текст напоминания:")
    await state.set_state(Form.waiting_for_reminder_text)

@dp.message(Form.waiting_for_reminder_text)
async def set_reminder_datetime(message: types.Message, state: FSMContext):
    await state.update_data(reminder_text=message.text)
    await message.answer("Введи дату и время напоминания в формате ГГГГ-ММ-ДД ЧЧ:ММ (например, 2025-08-20 14:30):")
    await state.set_state(Form.waiting_for_reminder_datetime)

@dp.message(Form.waiting_for_reminder_datetime)
async def save_reminder(message: types.Message, state: FSMContext):
    global next_reminder_id
    try:
        dt = datetime.strptime(message.text.strip(), "%Y-%m-%d %H:%M")
        dt = UZBEK_TZ.localize(dt)
        if dt < datetime.now(UZBEK_TZ):
            await message.answer("Нельзя установить напоминание на прошлое время. Попробуй снова:")
            return
        data = await state.get_data()
        reminder = {
            "id": next_reminder_id,
            "user_id": message.from_user.id,
            "datetime": dt,
            "text": data["reminder_text"]
        }
        reminders.append(reminder)
        next_reminder_id += 1
        await message.answer(f"✅ Напоминание сохранено на {dt.strftime('%d.%m.%Y %H:%M')}:\n{data['reminder_text']}", reply_markup=main_kb)
        await state.clear()
    except ValueError:
        await message.answer("Неверный формат. Введи в формате ГГГГ-ММ-ДД ЧЧ:ММ")

# --- Редактирование напоминаний ---
@dp.message(F.text == "✏ Редактировать напоминание")
async def edit_reminder_start(message: types.Message, state: FSMContext):
    user_reminders = [r for r in reminders if r["user_id"] == message.from_user.id]
    if not user_reminders:
        await message.answer("У тебя нет сохраненных напоминаний.", reply_markup=main_kb)
        return
    text = "Выбери ID напоминания для редактирования:\n" + "\n".join(f"{r['id']}: {r['text']} ({r['datetime'].strftime('%d.%m %H:%M')})" for r in user_reminders)
    await message.answer(text)
    await state.set_state(Form.editing_reminder_id)

@dp.message(Form.editing_reminder_id)
async def edit_reminder_select(message: types.Message, state: FSMContext):
    try:
        rid = int(message.text.strip())
        if not any(r["id"] == rid and r["user_id"] == message.from_user.id for r in reminders):
            await message.answer("Неверный ID. Попробуй снова:")
            return
        await state.update_data(edit_id=rid)
        await message.answer("Введи новый текст напоминания:")
        await state.set_state(Form.editing_reminder_text)
    except ValueError:
        await message.answer("Введите числовой ID.")

@dp.message(Form.editing_reminder_text)
async def edit_reminder_save(message: types.Message, state: FSMContext):
    data = await state.get_data()
    rid = data["edit_id"]
    for r in reminders:
        if r["id"] == rid:
            r["text"] = message.text
            await message.answer(f"✅ Напоминание {rid} обновлено.", reply_markup=main_kb)
            break
    await state.clear()

# --- Удаление напоминаний ---
@dp.message(F.text == "❌ Удалить напоминание")
async def delete_reminder(message: types.Message):
    user_reminders = [r for r in reminders if r["user_id"] == message.from_user.id]
    if not user_reminders:
        await message.answer("У тебя нет сохраненных напоминаний.", reply_markup=main_kb)
        return
    text = "Выбери ID напоминания для удаления:\n" + "\n".join(f"{r['id']}: {r['text']} ({r['datetime'].strftime('%d.%m %H:%M')})" for r in user_reminders)
    await message.answer(text)
    # Следующий шаг — ввод ID и удаление через обычное сообщение
    # Для упрощения пользователь вводит ID, бот удаляет:
    @dp.message()
    async def delete_by_id(msg: types.Message):
        try:
            rid = int(msg.text.strip())
            for r in reminders:
                if r["id"] == rid and r["user_id"] == msg.from_user.id:
                    reminders.remove(r)
                    await msg.answer(f"✅ Напоминание {rid} удалено.", reply_markup=main_kb)
                    return
            await msg.answer("Неверный ID.")
        except ValueError:
            await msg.answer("Введите числовой ID.")

# --- Фоновая проверка напоминаний ---
async def reminder_loop():
    while True:
        now = datetime.now(UZBEK_TZ)
        for r in reminders.copy():
            if now >= r["datetime"]:
                try:
                    await bot.send_message(ADMIN_CHAT_ID, f"🔔 Напоминание от {user_data.get(r['user_id'], 'Пользователь')}:\n{r['text']}")
                    reminders.remove(r)
                except Exception as e:
                    logger.error(f"Ошибка отправки напоминания: {e}")
        await asyncio.sleep(30)

# --- Запуск ---
async def main():
    asyncio.create_task(reminder_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
