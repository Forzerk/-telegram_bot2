from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio

TOKEN = "8306438881:AAEFg_MpnXk_iY2zHA5cGJomFv_kVAygbLk"
ADMIN_CHAT_ID = 5612586446

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# FSM состояния
class Form(StatesGroup):
    waiting_for_name = State()

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

# Команда /start
@dp.message(Command(commands=["start"]))
async def start_command(message: types.Message, state: FSMContext):
    await message.answer("Привет!\nПеред отправкой отчётов, пожалуйста, введи своё имя:")
    await state.set_state(Form.waiting_for_name)

# Получение имени
@dp.message(Form.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer(f"Спасибо, {message.text}! Теперь можешь отправлять отчёты 👇", reply_markup=main_kb)
    await message.answer("Отправь отчёт в виде текста, документа или фото.")
    await state.clear()  # очищаем состояние, чтобы клавиатура работала нормально

# Отправка отчета
@dp.message(F.text == "📤 Отправить отчет")
async def send_report(message: types.Message):
    await message.answer("Пришлите текст, фото или файл отчета, и я перешлю администратору.")

# Получение файлов, фото и текста
@dp.message(F.content_type.in_({"text", "photo", "document"}))
async def forward_to_admin(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_name = data.get("name", message.from_user.first_name)
    
    if message.content_type == "text":
        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"{user_name} прислал отчет:\n{message.text}")
        await message.answer("Текст принят и отправлен.")
    elif message.content_type == "photo":
        await bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=message.photo[-1].file_id, caption=f"{user_name} прислал фото: {message.caption or ''}")
        await message.answer("Фото принято и отправлено.")
    elif message.content_type == "document":
        await bot.send_document(chat_id=ADMIN_CHAT_ID, document=message.document.file_id, caption=f"{user_name} прислал файл: {message.caption or ''}")
        await message.answer("Файл принят и отправлен.")

# Заглушки для напоминаний
@dp.message(F.text == "📌 Установить напоминание")
async def set_reminder(message: types.Message):
    await message.answer("Напишите напоминание в формате '10:30 Сделать отчет'")

@dp.message(F.text == "✏ Редактировать напоминание")
async def edit_reminder(message: types.Message):
    await message.answer("Функция редактирования пока примерная, пришлите новое сообщение напоминания.")

@dp.message(F.text == "❌ Удалить напоминание")
async def delete_reminder(message: types.Message):
    await message.answer("Функция удаления напоминаний пока примерная.")

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
