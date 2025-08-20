import asyncio
from aiogram import Bot, Dispatcher, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime
import pytz
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = "8306438881:AAEFg_MpnXk_iY2zHA5cGJomFv_kVAygbLk"
ADMIN_CHAT_ID = 5612586446

# Установим узбекский часовой пояс (Asia/Tashkent)
UZBEK_TZ = pytz.timezone('Asia/Tashkent')

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
reminders = []  # Каждый элемент: {"user_id": int, "datetime": datetime, "text": str, "id": int}

# Генератор ID для напоминаний
next_reminder_id = 1

# --- Старт ---
@dp.message(F.text == "/start")
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer("Привет!\nПеред отправкой отчётов, пожалуйста, введи своё имя:")
    await state.set_state(Form.waiting_for_name)

@dp.message(Form.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    user_names[message.from_user.id] = message.text.strip()
    await message.answer(f"Спасибо, {user_names[message.from_user.id]}! Теперь можешь отправлять отчёты 👇", reply_markup=main_kb)
    await state.clear()

# --- Отчеты ---
@dp.message(F.text == "📤 Отправить отчет")
async def send_report(message: types.Message, state: FSMContext):
    if message.from_user.id not in user_names:
        await message.answer("Пожалуйста, сначала введите свое имя с помощью команды /start")
        return
        
    await message.answer("Отправь отчёт в виде текста, фото или документа:")
    await state.set_state(Form.waiting_for_report)

@dp.message(Form.waiting_for_report)
async def forward_report(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in user_names:
        await message.answer("Ошибка: имя пользователя не найдено. Пожалуйста, начните с /start")
        await state.clear()
        return
        
    name = user_names[user_id]
    
    try:
        if message.text:
            report_text = f"📋 Отчет от {name}\n\n{message.text}"
            await bot.send_message(chat_id=ADMIN_CHAT_ID, text=report_text)
            await message.answer("✅ Отчет успешно отправлен!", reply_markup=main_kb)
            
        elif message.photo:
            caption = f"📷 Фото-отчет от {name}"
            if message.caption:
                caption += f"\n\n{message.caption}"
                
            await bot.send_photo(
                chat_id=ADMIN_CHAT_ID,
                photo=message.photo[-1].file_id,
                caption=caption
            )
            await message.answer("✅ Фото-отчет успешно отправлен!", reply_markup=main_kb)
            
        elif message.document:
            caption = f"📄 Документ-отчет от {name}"
            if message.caption:
                caption += f"\n\n{message.caption}"
                
            await bot.send_document(
                chat_id=ADMIN_CHAT_ID,
                document=message.document.file_id,
                caption=caption
            )
            await message.answer("✅ Документ-отчет успешно отправлен!", reply_markup=main_kb)
            
        else:
            await message.answer("Пожалуйста, отправьте текст, фото или документ")
            return
            
    except Exception as e:
        logger.error(f"Ошибка при отправке отчета: {e}")
        await message.answer("❌ Ошибка при отправке отчета. Попробуйте еще раз.")
    
    await state.clear()

# --- Напоминания ---
@dp.message(F.text == "📌 Установить напоминание")
async def set_reminder_date(message: types.Message, state: FSMContext):
    await message.answer("Введи дату напоминания в формате ГГГГ-ММ-ДД (например, 2025-08-20):")
    await state.set_state(Form.waiting_for_reminder_date)

@dp.message(Form.waiting_for_reminder_date)
async def set_reminder_time(message: types.Message, state: FSMContext):
    try:
        date_str = message.text.strip()
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
        today = datetime.now(UZBEK_TZ).date()
        
        if date < today:
            await message.answer("Нельзя установить напоминание на прошедшую дату. Введи корректную дату:")
            return
            
        await state.update_data(reminder_date=date)
        await message.answer("Введи время напоминания в формате ЧЧ:ММ (например, 14:30):")
        await state.set_state(Form.waiting_for_reminder_time)
    except ValueError:
        await message.answer("Неверный формат даты. Попробуй снова ГГГГ-ММ-ДД (например, 2025-08-20).")

@dp.message(Form.waiting_for_reminder_time)
async def set_reminder_text(message: types.Message, state: FSMContext):
    try:
        time_str = message.text.strip()
        time = datetime.strptime(time_str, "%H:%M").time()
        
        data = await state.get_data()
        date = data['reminder_date']
        
        dt = datetime.combine(date, time)
        dt = UZBEK_TZ.localize(dt)
        
        if dt < datetime.now(UZBEK_TZ):
            await message.answer("Нельзя установить напоминание на прошедшее время. Введи корректное время:")
            return
            
        await state.update_data(reminder_datetime=dt)
        await message.answer("Напиши текст напоминания:")
        await state.set_state(Form.waiting_for_reminder_text)
    except ValueError:
        await message.answer("Неверный формат времени. Попробуй снова ЧЧ:ММ (например, 14:30).")

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

    edit_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("✏️ Редактировать", callback_data=f"edit_{reminder['id']}")]
    ])

    await message.answer(
        f"✅ Напоминание сохранено на {dt.strftime('%d.%m.%Y %H:%M')}:\n{message.text}", 
        reply_markup=main_kb
    )
    await message.answer("Хочешь отредактировать?", reply_markup=edit_kb)
    await state.clear()

# --- Редактирование напоминаний ---
@dp.callback_query(F.data.startswith("edit_"))
async def edit_reminder(query: types.CallbackQuery, state: FSMContext):
    reminder_id = int(query.data.split("_")[1])
    
    reminder = next((r for r in reminders if r["id"] == reminder_id), None)
    
    if not reminder:
        await query.message.answer("Напоминание не найдено или уже сработало.")
        await query.answer()
        return
        
    if reminder["datetime"] < datetime.now(UZBEK_TZ):
        await query.message.answer("Это напоминание уже сработало и не может быть изменено.")
        await query.answer()
        return
        
    await state.update_data(edit_id=reminder_id)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("📅 Изменить дату", callback_data="edit_date")],
        [InlineKeyboardButton("⏰ Изменить время", callback_data="edit_time")],
        [InlineKeyboardButton("📝 Изменить текст", callback_data="edit_text")],
        [InlineKeyboardButton("🗑️ Удалить", callback_data=f"delete_{reminder_id}")]
    ])
    
    await query.message.answer("Что хочешь изменить?", reply_markup=kb)
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

@dp.message(Form.editing_date)
async def save_edited_date(message: types.Message, state: FSMContext):
    try:
        new_date = datetime.strptime(message.text, "%Y-%m-%d").date()
        
        if new_date < datetime.now(UZBEK_TZ).date():
            await message.answer("Нельзя установить напоминание на прошедшую дату. Введи корректную дату:")
            return
            
        data = await state.get_data()
        reminder_id = data['edit_id']
        
        for reminder in reminders:
            if reminder["id"] == reminder_id:
                old_dt = reminder["datetime"]
                new_dt = UZBEK_TZ.localize(datetime.combine(new_date, old_dt.time()))
                
                if new_dt < datetime.now(UZBEK_TZ):
                    await message.answer("Нельзя установить напоминание на прошедшее время. Введи корректную дату:")
                    return
                
                reminder["datetime"] = new_dt
                await message.answer(
                    f"✅ Дата напоминания обновлена! Новое время: {new_dt.strftime('%d.%m.%Y %H:%M')}", 
                    reply_markup=main_kb
                )
                break
    except ValueError:
        await message.answer("Неверный формат даты. Попробуй снова ГГГГ-ММ-ДД.")
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
                
                if new_dt < datetime.now(UZBEK_TZ):
                    await message.answer("Нельзя установить напоминание на прошедшее время. Введи корректное время:")
                    return
                
                reminder["datetime"] = new_dt
                await message.answer(
                    f"✅ Время напоминания обновлено! Новое время: {new_dt.strftime('%d.%m.%Y %H:%M')}", 
                    reply_markup=main_kb
                )
                break
    except ValueError:
        await message.answer("Неверный формат времени. Попробуй снова ЧЧ:ММ.")
    await state.clear()

@dp.message(Form.editing_text)
async def save_edited_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    reminder_id = data['edit_id']
    
    for reminder in reminders:
        if reminder["id"] == reminder_id:
            reminder["text"] = message.text
            await message.answer(
                f"✅ Текст напоминания обновлен!\nНовый текст: {message.text}", 
                reply_markup=main_kb
            )
            break
            
    await state.clear()

# --- Фоновая проверка напоминаний ---
async def reminder_loop():
    while True:
        now = datetime.now(UZBEK_TZ)
        for reminder in reminders.copy():
            dt, text, user_id = reminder["datetime"], reminder["text"], reminder["user_id"]
            if now >= dt:
                try:
                    await bot.send_message(
                        chat_id=user_id, 
                        text=f"🔔 Напоминание:\n{text}"
                    )
                    reminders.remove(reminder)
                except Exception as e:
                    print(f"Ошибка отправки напоминания: {e}")
        await asyncio.sleep(30)

async def main():
    asyncio.create_task(reminder_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())