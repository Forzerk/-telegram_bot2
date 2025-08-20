from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram import F
import asyncio
from aiogram.fsm.storage.memory import MemoryStorage

TOKEN = "8306438881:AAEFg_MpnXk_iY2zHA5cGJomFv_kVAygbLk"
ADMIN_CHAT_ID = 5612586446

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

# Команда /start
@dp.message(Command(commands=["start"]))
async def start_command(message: types.Message):
    await message.answer(
        "Привет! Я бот для отправки отчетов и напоминаний.",
        reply_markup=main_kb
    )

# Отправка отчета
@dp.message(F.text == "📤 Отправить отчет")
async def send_report(message: types.Message):
    await message.answer("Пришлите текст, фото или файл отчета, и я перешлю администратору.")

# Получение файлов, фото и текста
@dp.message(F.content_type.in_({"text", "photo", "document"}))
async def forward_to_admin(message: types.Message):
    if message.content_type == "text":
        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=message.text)
    elif message.content_type == "photo":
        await bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=message.photo[-1].file_id, caption=message.caption)
    elif message.content_type == "document":
        await bot.send_document(chat_id=ADMIN_CHAT_ID, document=message.document.file_id, caption=message.caption)
    await message.answer("Отчет отправлен!")

# Напоминания (пока заглушки)
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
