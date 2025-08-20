import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from datetime import datetime
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# === ТОКЕН И ID ГРУППЫ ===
TOKEN = "8306438881:AAEFg_MpnXk_iY2zHA5cGJomFv_kVAygbLk"
ADMIN_CHAT_ID = -4936649070  # Твой ID группы

# === БОТ И ДИСПЕТЧЕР ===
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# === КЛАВИАТУРЫ ===
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📤 Отправить отчет")],
        [KeyboardButton(text="📌 Установить напоминание")],
        [KeyboardButton(text="✏ Редактировать напоминание")],
    ],
    resize_keyboard=True
)

edit_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Дата", callback_data="edit_date"),
            InlineKeyboardButton(text="Время", callback_data="edit_time"),
            InlineKeyboardButton(text="Содержание", callback_data="edit_text"),
        ]
    ]
)

# === FSM ===
class Form(StatesGroup):
    waiting_for_name = State()
    waiting_for_report = State()
    reminder_date = State()
    reminder_time = State()
    reminder_text = State()
    editing_choice = State()
    editing_value = State()

# === ХРАНИЛИЩА ===
user_names = {}  # user_id -> name
reminders = []   # список (datetime, text, user_id)

# === /start ===
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer("Привет! Введи своё имя для отчетов:", reply_markup=main_kb)
    await state.set_state(Form.waiting_for_name)

@dp.message(Form.waiting_for_name, F.text)
async def process_name(message: types.Message, state: FSMContext):
    user_names[message.from_user.id] = message.text
    await message.answer(f"Спасибо, {message.text}! Теперь можешь отправлять отчёты и устанавливать напоминания.", reply_markup=main_kb)
    await state.clear()

# === ОТПРАВКА ОТЧЁТА ===
@dp.message(F.text == "📤 Отправить отчет")
async def send_report(message: types.Message, state: FSMContext):
    if message.from_user.id not in user_names:
        await message.answer("Сначала введи имя через /start")
        return
    await message.answer("Отправь отчет (текст, фото или документ):")
    await state.set_state(Form.waiting_for_report)

@dp.message(Form.waiting_for_report)
async def forward_report(message: types.Message, state: FSMContext):
    name = user_names.get(message.from_user.id, "Пользователь")
    try:
        if message.content_type == "text":
            await bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"📋 Отчет от {name}:\n\n{message.text}"
            )
        elif message.content_type == "photo":
            caption = f"📷 Фото-отчет от {name}\n{message.caption or ''}"
            await bot.send_photo(
                chat_id=ADMIN_CHAT_ID,
                photo=message.photo[-1].file_id,
                caption=caption
            )
        elif message.content_type == "document":
            caption = f"📄 Документ-отчет от {name}\n{message.caption or ''}"
            await bot.send_document(
                chat_id=ADMIN_CHAT_ID,
                document=message.document.file_id,
                caption=caption
            )
        await message.answer("✅ Отчет отправлен!", reply_markup=main_kb)
    except Exception as e:
        await message.answer("❌ Не удалось отправить отчет. Попробуй снова позже.")
        logging.error(f"Ошибка отправки отчета: {e}")
    await state.clear()

# === УСТАНОВКА НАПОМИНАНИЯ ===
@dp.message(F.text == "📌 Установить напоминание")
async def set_reminder(message: types.Message, state: FSMContext):
    await message.answer("Введи дату в формате YYYY-MM-DD:")
    await state.set_state(Form.reminder_date)

@dp.message(Form.reminder_date, F.text)
async def process_date(message: types.Message, state: FSMContext):
    try:
        datetime.strptime(message.text, "%Y-%m-%d")
        await state.update_data(reminder_date=message.text)
        await message.answer("Теперь введи время в формате HH:MM:")
        await state.set_state(Form.reminder_time)
    except ValueError:
        await message.answer("❌ Неверный формат даты. Попробуй снова: YYYY-MM-DD")

@dp.message(Form.reminder_time, F.text)
async def process_time(message: types.Message, state: FSMContext):
    try:
        datetime.strptime(message.text, "%H:%M")
        await state.update_data(reminder_time=message.text)
        await message.answer("Теперь введи текст напоминания:")
        await state.set_state(Form.reminder_text)
    except ValueError:
        await message.answer("❌ Неверный формат времени. Попробуй снова: HH:MM")

@dp.message(Form.reminder_text, F.text)
async def process_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    dt_str = f"{data['reminder_date']} {data['reminder_time']}"
    try:
        reminder_dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        reminders.append((reminder_dt, message.text, message.from_user.id))
        await message.answer(
            f"✅ Напоминание установлено на {reminder_dt.strftime('%Y-%m-%d %H:%M')}: {message.text}",
            reply_markup=main_kb
        )
    except Exception as e:
        await message.answer("❌ Ошибка при установке напоминания.")
        logging.error(f"Ошибка парсинга времени: {e}")
    await state.clear()

# === РЕДАКТИРОВАНИЕ НАПОМИНАНИЯ ===
@dp.message(F.text == "✏ Редактировать напоминание")
async def edit_reminder(message: types.Message, state: FSMContext):
    user_rems = [r for r in reminders if r[2] == message.from_user.id]
    if not user_rems:
        await message.answer("У тебя нет сохранённых напоминаний.")
        return
    # Возьмём последнее напоминание (можно улучшить — показывать список)
    reminder = user_rems[-1]
    index = reminders.index(reminder)
    await state.update_data(editing_reminder_index=index)
    await message.answer("Что хочешь изменить?", reply_markup=edit_kb)

@dp.callback_query(F.data.startswith("edit_"))
async def process_edit_choice(callback: types.CallbackQuery, state: FSMContext):
    choice = callback.data.split("_", 1)[1]  # date, time, text
    await state.update_data(edit_choice=choice)
    if choice == "date":
        await callback.message.answer("Введи новую дату (YYYY-MM-DD):")
    elif choice == "time":
        await callback.message.answer("Введи новое время (HH:MM):")
    elif choice == "text":
        await callback.message.answer("Введи новый текст напоминания:")
    await state.set_state(Form.editing_value)

@dp.message(Form.editing_value, F.text)
async def save_edited_reminder(message: types.Message, state: FSMContext):
    data = await state.get_data()
    choice = data.get("edit_choice")
    index = data.get("editing_reminder_index")

    if index is None or index >= len(reminders):
        await message.answer("❌ Напоминание не найдено.")
        await state.clear()
        return

    reminder = reminders[index]
    if reminder[2] != message.from_user.id:
        await message.answer("❌ Ты не можешь редактировать это напоминание.")
        await state.clear()
        return

    try:
        dt, text, user_id = reminder
        if choice == "date":
            new_date = datetime.strptime(message.text, "%Y-%m-%d").date()
            new_dt = datetime.combine(new_date, dt.time())
            reminders[index] = (new_dt, text, user_id)
            display = new_dt
        elif choice == "time":
            new_time = datetime.strptime(message.text, "%H:%M").time()
            new_dt = datetime.combine(dt.date(), new_time)
            reminders[index] = (new_dt, text, user_id)
            display = new_dt
        elif choice == "text":
            reminders[index] = (dt, message.text, user_id)
            display = dt
        else:
            await message.answer("❌ Неизвестное действие.")
            await state.clear()
            return

        await message.answer(
            f"✅ Напоминание обновлено: {display.strftime('%Y-%m-%d %H:%M')} — {reminders[index][1]}",
            reply_markup=main_kb
        )
    except ValueError:
        await message.answer("❌ Неверный формат. Попробуй ещё раз.")
    except Exception as e:
        await message.answer("❌ Ошибка при редактировании.")
        logging.error(f"Ошибка редактирования: {e}")
    await state.clear()

# === ФОНОВЫЙ ЦИКЛ НАПОМИНАНИЙ ===
async def reminder_loop():
    while True:
        try:
            now = datetime.now()
            for reminder in reminders.copy():
                dt, text, user_id = reminder
                if now >= dt:
                    try:
                        name = user_names.get(user_id, "Пользователь")
                        await bot.send_message(
                            chat_id=ADMIN_CHAT_ID,
                            text=f"⏰ Напоминание от {name}: {text}"
                        )
                        reminders.remove(reminder)
                    except Exception as e:
                        logging.error(f"❌ Ошибка отправки напоминания: {e}")
        except Exception as e:
            logging.error(f"❌ Ошибка в цикле напоминаний: {e}")
        await asyncio.sleep(30)

# === ЗАПУСК ===
async def main():
    # Запускаем фоновую задачу
    asyncio.create_task(reminder_loop())
    logging.info("Бот запущен. Ожидание сообщений...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
