import asyncio
from aiogram import Bot, Dispatcher, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime
import pytz
import logging

# --- Логирование ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Токен и группа ---
TOKEN = "8306438881:AAEFg_MpnXk_iY2zHA5cGJomFv_kVAygbLk"
GROUP_CHAT_ID = -1002773998221  # сюда приходят отчеты и напоминания

# --- Часовой пояс ---
UZBEK_TZ = pytz.timezone('Asia/Tashkent')

# --- Инициализация бота ---
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- Клавиатура ---
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("📤 Отправить отчет")],
        [KeyboardButton("📌 Установить напоминание")]
    ],
    resize_keyboard=True
)

# --- FSM ---
class Form(StatesGroup):
    waiting_for_name = State()
    waiting_for_report = State()
    waiting_for_reminder_date = State()
    waiting_for_reminder_time = State()
    waiting_for_reminder_text = State()
    editing_date = State()
    editing_time = State()
    editing_text = State()

# --- Хранилище ---
user_names = {}
reminders = []
next_reminder_id = 1

# --- Старт ---
@dp.message(F.text == "/start")
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer("Привет!\nПеред отправкой отчётов, пожалуйста, введи своё имя:")
    await state.set_state(Form.waiting_for_name)

@dp.message(Form.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    user_names[message.from_user.id] = message.text.strip()
    await message.answer(f"Спасибо, {message.text}! Теперь можешь отправлять отчёты 👇", reply_markup=main_kb)
    await state.clear()

# --- Отчеты ---
@dp.message(F.text == "📤 Отправить отчет")
async def send_report(message: types.Message, state: FSMContext):
    if message.from_user.id not in user_names:
        await message.answer("Сначала введи своё имя через /start")
        return
    await message.answer("Отправь отчёт в виде текста, фото или документа:")
    await state.set_state(Form.waiting_for_report)

@dp.message(Form.waiting_for_report)
async def forward_report(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = user_names.get(user_id, "Пользователь")
    try:
        if message.content_type == "text":
            await bot.send_message(GROUP_CHAT_ID, f"📋 Отчет от {name}\n\n{message.text}")
        elif message.content_type == "photo":
            caption = f"📷 Фото-отчет от {name}"
            if message.caption:
                caption += f"\n\n{message.caption}"
            await bot.send_photo(GROUP_CHAT_ID, photo=message.photo[-1].file_id, caption=caption)
        elif message.content_type == "document":
            caption = f"📄 Документ-отчет от {name}"
            if message.caption:
                caption += f"\n\n{message.caption}"
            await bot.send_document(GROUP_CHAT_ID, document=message.document.file_id, caption=caption)
        else:
            await message.answer("Пожалуйста, отправьте текст, фото или документ")
            return
        await message.answer("✅ Отчет успешно отправлен!", reply_markup=main_kb)
    except Exception as e:
        logger.error(f"Ошибка при отправке отчета: {e}")
        await message.answer("❌ Ошибка при отправке отчета. Попробуйте еще раз.")
    await state.clear()

# --- Напоминания ---
@dp.message(F.text == "📌 Установить напоминание")
async def set_reminder_date(message: types.Message, state: FSMContext):
    await message.answer("Введи дату напоминания в формате ГГГГ-ММ-ДД:")
    await state.set_state(Form.waiting_for_reminder_date)

@dp.message(Form.waiting_for_reminder_date)
async def set_reminder_time(message: types.Message, state: FSMContext):
    try:
        date_str = message.text.strip()
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
        if date < datetime.now(UZBEK_TZ).date():
            await message.answer("Нельзя установить напоминание на прошедшую дату. Введи корректную дату:")
            return
        await state.update_data(reminder_date=date)
        await message.answer("Введи время напоминания в формате ЧЧ:ММ:")
        await state.set_state(Form.waiting_for_reminder_time)
    except ValueError:
        await message.answer("Неверный формат даты. Попробуй снова ГГГГ-ММ-ДД.")

@dp.message(Form.waiting_for_reminder_time)
async def set_reminder_text(message: types.Message, state: FSMContext):
    try:
        time_str = message.text.strip()
        time = datetime.strptime(time_str, "%H:%M").time()
        data = await state.get_data()
        date = data['reminder_date']
        dt = UZBEK_TZ.localize(datetime.combine(date, time))
        if dt < datetime.now(UZBEK_TZ):
            await message.answer("Нельзя установить напоминание на прошедшее время. Введи корректное время:")
            return
        await state.update_data(reminder_datetime=dt)
        await message.answer("Напиши текст напоминания:")
        await state.set_state(Form.waiting_for_reminder_text)
    except ValueError:
        await message.answer("Неверный формат времени. Попробуй снова ЧЧ:ММ.")

@dp.message(Form.waiting_for_reminder_text)
async def save_reminder(message: types.Message, state: FSMContext):
    global next_reminder_id
    data = await state.get_data()
    dt = data['reminder_datetime']

    reminder = {
        "id": next_reminder_id,
        "user_id": message.from_user.id,
        "datetime": dt,
        "text": message.text
    }
    reminders.append(reminder)
    next_reminder_id += 1

    # Кнопки редактирования и удаления
    edit_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("✏️ Редактировать", callback_data=f"edit_{reminder['id']}")],
        [InlineKeyboardButton("🗑️ Удалить", callback_data=f"delete_{reminder['id']}")]
    ])

    await message.answer(
        f"✅ Напоминание сохранено на {dt.strftime('%d.%m.%Y %H:%M')}:\n{message.text}",
        reply_markup=edit_kb
    )
    await state.clear()

# --- Редактирование и удаление ---
@dp.callback_query(F.data.startswith("edit_"))
async def edit_reminder(query: types.CallbackQuery, state: FSMContext):
    reminder_id = int(query.data.split("_")[1])
    reminder = next((r for r in reminders if r["id"] == reminder_id), None)
    if not reminder:
        await query.message.answer("Напоминание не найдено.")
        await query.answer()
        return
    await state.update_data(edit_id=reminder_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("📅 Изменить дату", callback_data="edit_date")],
        [InlineKeyboardButton("⏰ Изменить время", callback_data="edit_time")],
        [InlineKeyboardButton("📝 Изменить текст", callback_data="edit_text")]
    ])
    await query.message.answer("Что хочешь изменить?", reply_markup=kb)
    await query.answer()

@dp.callback_query(F.data.startswith("delete_"))
async def delete_reminder(query: types.CallbackQuery):
    reminder_id = int(query.data.split("_")[1])
    for i, reminder in enumerate(reminders):
        if reminder["id"] == reminder_id:
            del reminders[i]
            await query.message.answer("✅ Напоминание удалено!", reply_markup=main_kb)
            await query.answer()
            return
    await query.message.answer("Напоминание не найдено.")
    await query.answer()

@dp.callback_query(F.data == "edit_date")
async def edit_date(query: types.CallbackQuery, state: FSMContext):
    await query.message.answer("Введи новую дату в формате ГГГГ-ММ-ДД:")
    await state.set_state(Form.editing_date)
    await query.answer()

@dp.callback_query(F.data == "edit_time")
async def edit_time(query: types.CallbackQuery, state: FSMContext):
    await query.message.answer("Введи новое время в формате ЧЧ:ММ:")
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
        reminder_id = data['edit_id']
        for reminder in reminders:
            if reminder["id"] == reminder_id:
                old_dt = reminder["datetime"]
                new_dt = UZBEK_TZ.localize(datetime.combine(new_date, old_dt.time()))
                reminder["datetime"] = new_dt
                await message.answer(f"✅ Дата обновлена: {new_dt.strftime('%d.%m.%Y %H:%M')}", reply_markup=main_kb)
                break
    except ValueError:
        await message.answer("Неверный формат даты.")
    await state.clear()

@dp.message(Form.editing_time)
async def save_edited_time(message: types.Message, state: FSMContext):
    try:
        new_time = datetime.strptime(message.text, "%H:%M").time()
        data = await state.get_data()
        reminder_id = data['edit_id']
        for reminder in reminders:
            if reminder["id"] == reminder_id:
                old_dt = reminder["datetime"]
                new_dt = UZBEK_TZ.localize(datetime.combine(old_dt.date(), new_time))
                reminder["datetime"] = new_dt
                await message.answer(f"✅ Время обновлено: {new_dt.strftime('%d.%m.%Y %H:%M')}", reply_markup=main_kb)
                break
    except ValueError:
        await message.answer("Неверный формат времени.")
    await state.clear()

@dp.message(Form.editing_text)
async def save_edited_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    reminder_id = data['edit_id']
    for reminder in reminders:
        if reminder["id"] == reminder_id:
            reminder["text"] = message.text
            await message.answer(f"✅ Текст обновлен:\n{message.text}", reply_markup=main_kb)
            break
    await state.clear()

# --- Фоновая проверка напоминаний ---
async def reminder_loop():
    while True:
        now = datetime.now(UZBEK_TZ)
        for reminder in reminders.copy():
            dt, text = reminder["datetime"], reminder["text"]
            if now >= dt:
                try:
                    await bot.send_message(GROUP_CHAT_ID, f"🔔 Напоминание:\n{text}")
                    reminders.remove(reminder)
                except Exception as e:
                    logger.error(f"Ошибка отправки напоминания: {e}")
        await asyncio.sleep(30)

# --- Запуск ---
async def main():
    asyncio.create_task(reminder_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

