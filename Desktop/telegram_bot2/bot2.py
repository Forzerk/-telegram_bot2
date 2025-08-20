import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz

# ==========================
API_TOKEN = "8306438881:AAEFg_MpnXk_iY2zHA5cGJomFv_kVAygbLk"
TARGET_CHAT_ID = 5612586446  # чат, куда пересылаем отчёты и напоминания
# ==========================

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

scheduler = AsyncIOScheduler(timezone=pytz.timezone("Asia/Tashkent"))

# Хранение данных
users = {}      # {user_id: {"name": str}}
reminders = {}  # {user_id: {"day": int, "time": str, "text": str, "job_id": str}}
user_state = {} # хранит состояние пользователя для установки/редактирования


# --- КНОПКИ ---
def main_menu():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📌 Установить напоминание", callback_data="set_reminder"))
    kb.add(InlineKeyboardButton("✏ Редактировать напоминание", callback_data="edit_reminder"))
    kb.add(InlineKeyboardButton("❌ Удалить напоминание", callback_data="delete_reminder"))
    kb.add(InlineKeyboardButton("Отправить отчёт", callback_data="send_report"))
    return kb

def days_menu():
    kb = InlineKeyboardMarkup(row_width=3)
    days = ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]
    for i, d in enumerate(days, start=1):
        kb.insert(InlineKeyboardButton(d, callback_data=f"day_{i}"))
    return kb

def times_menu():
    kb = InlineKeyboardMarkup(row_width=4)
    for h in range(9, 23):
        kb.insert(InlineKeyboardButton(f"{h}:00", callback_data=f"time_{h}:00"))
    return kb


# --- СТАРТ ---
@dp.message_handler(commands=["start"])
async def start_cmd(message: types.Message):
    user_state[message.from_user.id] = "waiting_name"
    await message.answer("👋 Привет! Напиши своё имя:")


# --- СОХРАНЕНИЕ ИМЕНИ ---
@dp.message_handler(lambda msg: user_state.get(msg.from_user.id) == "waiting_name")
async def set_name(message: types.Message):
    users[message.from_user.id] = {"name": message.text}
    user_state[message.from_user.id] = None
    await message.answer(
        f"✅ Имя сохранено: {message.text}\n\nТеперь можешь отправлять отчёты или настраивать напоминания.",
        reply_markup=main_menu()
    )


# --- ПЕРЕСЫЛКА ОТЧЁТОВ ---
@dp.message_handler(content_types=types.ContentTypes.ANY)
async def forward_report(message: types.Message):
    if message.from_user.id not in users:
        await message.answer("❗ Сначала введи имя командой /start")
        return

    user_name = users[message.from_user.id]["name"]
    caption = f"👤 Отчёт от: {user_name}\n\n"

    if message.text:
        await bot.send_message(TARGET_CHAT_ID, f"{caption}{message.text}")
    elif message.photo:
        await bot.send_photo(TARGET_CHAT_ID, message.photo[-1].file_id, caption=caption + (message.caption or ""))
    elif message.document:
        await bot.send_document(TARGET_CHAT_ID, message.document.file_id, caption=caption + (message.caption or ""))
    else:
        await message.forward(TARGET_CHAT_ID)


# --- УСТАНОВКА НАПОМИНАНИЯ ---
@dp.callback_query_handler(lambda c: c.data == "set_reminder")
async def set_reminder(call: types.CallbackQuery):
    await call.message.answer("Выберите день недели:", reply_markup=days_menu())
    user_state[call.from_user.id] = "setting_day"
    await call.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("day_"))
async def set_day(call: types.CallbackQuery):
    uid = call.from_user.id
    day_num = int(call.data.split("_")[1])
    if uid not in reminders:
        reminders[uid] = {}
    state = user_state.get(uid)
    if state in ["setting_day", "editing_day"]:
        reminders[uid]["day"] = day_num
        await call.message.answer("Теперь выберите время:", reply_markup=times_menu())
        user_state[uid] = "setting_time" if state == "setting_day" else "editing_time"
    await call.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("time_"))
async def set_time(call: types.CallbackQuery):
    uid = call.from_user.id
    time_str = call.data.split("_")[1]
    state = user_state.get(uid)
    if state in ["setting_time", "editing_time"]:
        reminders[uid]["time"] = time_str
        await call.message.answer("✍ Введите текст напоминания:")
        user_state[uid] = "setting_text" if state == "setting_time" else "editing_text"
    await call.answer()

@dp.message_handler(lambda message: user_state.get(message.from_user.id) in ["setting_text", "editing_text"])
async def set_text(message: types.Message):
    uid = message.from_user.id
    reminders[uid]["text"] = message.text
    state = user_state[uid]
    user_state[uid] = None

    # Удаляем старую задачу, если была
    if "job_id" in reminders[uid]:
        try:
            scheduler.remove_job(reminders[uid]["job_id"])
        except:
            pass

    # Создаём новую задачу
    hour = int(reminders[uid]["time"].split(":")[0])
    job = scheduler.add_job(send_reminder, "cron",
                            day_of_week=reminders[uid]["day"]-1,
                            hour=hour,
                            minute=0,
                            args=[uid])
    reminders[uid]["job_id"] = job.id

    await message.answer(
        f"✅ Напоминание {'установлено' if state=='setting_text' else 'обновлено'}:\n"
        f"📅 День: {reminders[uid]['day']}\n⏰ Время: {reminders[uid]['time']}\n💬 Текст: {reminders[uid]['text']}",
        reply_markup=main_menu()
    )


# --- РЕДАКТИРОВАНИЕ НАПОМИНАНИЯ ---
@dp.callback_query_handler(lambda c: c.data == "edit_reminder")
async def edit_reminder(call: types.CallbackQuery):
    uid = call.from_user.id
    if uid not in reminders:
        await call.message.answer("❗ У тебя нет активных напоминаний.")
        return
    await call.message.answer("Выберите новый день недели:", reply_markup=days_menu())
    user_state[uid] = "editing_day"
    await call.answer()

# --- УДАЛЕНИЕ НАПОМИНАНИЯ ---
@dp.callback_query_handler(lambda c: c.data == "delete_reminder")
async def delete_reminder(call: types.CallbackQuery):
    uid = call.from_user.id
    if uid in reminders:
        try:
            scheduler.remove_job(reminders[uid]["job_id"])
        except:
            pass
        reminders.pop(uid)
        await call.message.answer("✅ Напоминание удалено.", reply_markup=main_menu())
    else:
        await call.message.answer("❗ У тебя нет активных напоминаний.", reply_markup=main_menu())
    await call.answer()


# --- ОТПРАВКА НАПОМИНАНИЯ В ГРУППУ ---
async def send_reminder(uid):
    if uid in reminders:
        text = reminders[uid]["text"]
        await bot.send_message(TARGET_CHAT_ID, f"🔔 Напоминание!\n\n{text}")


# --- ЗАПУСК ---
if __name__ == "__main__":
    scheduler.start()
    executor.start_polling(dp, skip_updates=True)
