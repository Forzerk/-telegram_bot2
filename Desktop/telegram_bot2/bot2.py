# Список разрешённых пользователей
ALLOWED_USERS = [123456789, 987654321]  # вставь сюда реальные Telegram ID

# Проверка при установке напоминания
@dp.message(F.text == "📌 Установить напоминание")
async def set_reminder_date(message: types.Message, state: FSMContext):
    if message.from_user.id not in ALLOWED_USERS:
        await message.answer("У тебя нет прав на установку напоминаний.", reply_markup=main_kb)
        return
    await message.answer("Введи дату напоминания в формате YYYY-MM-DD:")
    await state.set_state(Form.waiting_for_reminder_date)

# Проверка при редактировании
@dp.message(F.text == "✏ Редактировать напоминание")
async def edit_reminder(message: types.Message, state: FSMContext):
    if message.from_user.id not in ALLOWED_USERS:
        await message.answer("У тебя нет прав на редактирование напоминаний.", reply_markup=main_kb)
        return
    if not current_reminder:
        await message.answer("Сначала установи напоминание!", reply_markup=main_kb)
        return
    await message.answer("Выбери, что хочешь изменить:", reply_markup=edit_kb)
    await state.set_state(Form.waiting_for_edit_choice)
