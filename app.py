import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram import F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.state import State
from aiogram.fsm.state import StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from db import init_db, get_user, add_user, update_coins, SessionLocal, User
import random
from sqlalchemy.future import select
import os
from aiogram.types import FSInputFile


API_TOKEN = '7381987351:AAGFo5oor7_tUMdZwHvjT8ltT4BvyIHvbqc'

# Включаем логирование
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Инициализация базы данных
async def on_startup():
    await init_db()  # Инициализация базы данных

# Определение состояний
class Form(StatesGroup):
    main_menu = State()
    shop = State()
    stats = State()
    coinflip_side = State()
    coinflip_bet = State()
    guess_number_choice = State()  # Новое состояние для выбора числа
    guess_number_bet = State()     # Новое состояние для выбора ставки в игре с числами
    click_hamster = State()


# Команда старт
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    # Сохраняем user_id в состоянии
    await state.update_data(user_id=user_id)

    # Получаем данные состояния
    state_data = await state.get_data()

    async with SessionLocal() as session:
        if not await get_user(session, user_id):
            await add_user(session, user_id)  # Добавляем пользователя в БД

    await show_main_menu(message.chat.id, state)

def get_random_hamster_image():
    hamster_folder = 'hamsters/'  # Папка с изображениями
    hamster_images = os.listdir(hamster_folder)  # Получаем список файлов в папке
    print(hamster_images)
    random_image = random.choice(hamster_images)  # Выбираем случайное изображение
    print(random_image)
    return os.path.join(hamster_folder, random_image)  # Возвращаем полный путь к изображению

@dp.callback_query(StateFilter(Form.main_menu), F.data == 'show_hamster')
async def process_show_hamster(callback_query: types.CallbackQuery, state: FSMContext):
    hamster_image_path = get_random_hamster_image()  # Получаем случайное изображение
    print(f"hamster_image_path {hamster_image_path}")

    # Проверяем, существует ли файл
    if os.path.isfile(hamster_image_path):
        # Создаем объект InputFile
        photo = FSInputFile(hamster_image_path)  # Открываем файл

        # Отправляем изображение пользователю с подписью
        await bot.send_photo(
            chat_id=callback_query.from_user.id,
            photo=photo,
            caption="Вот ваш хомячок! 🐹",
            disable_notification=True  # Отключаем уведомления
        )
    else:
        await bot.send_message(callback_query.from_user.id, "Изображение не найдено.")

    # Возвращаемся в главное меню
    await show_main_menu(callback_query.from_user.id, state)


# Основное меню
async def show_main_menu(chat_id: int, state: FSMContext):
    state_data = await state.get_data()
    user_id = state_data['user_id']

    async with SessionLocal() as session:
        user = await get_user(session, user_id)  # Получаем пользователя по user_id

        button1 = types.InlineKeyboardButton(text="💰 Нажми на хомячка", callback_data='click_hamster')
        button2 = types.InlineKeyboardButton(text="🏆 Магазин", callback_data='shop')
        button3 = types.InlineKeyboardButton(text="🎮 Игры", callback_data='game_menu')
        button4 = types.InlineKeyboardButton(text="📊 Статистика по монетам", callback_data='stats')
        button5 = types.InlineKeyboardButton(text="🐹 Показать хомяка", callback_data='show_hamster')
        # Проверка на ваш ID
        if user_id == 1131742460:
            admin_button = types.InlineKeyboardButton(text="🔧 Админ-панель", callback_data='admin_panel')
            keyboard = types.InlineKeyboardMarkup(
                inline_keyboard=[[button1], [button2], [button3], [button4], [button5], [admin_button]])
        else:
            keyboard = types.InlineKeyboardMarkup(
                inline_keyboard=[[button1], [button2], [button3], [button4], [button5]])

        await bot.send_message(chat_id,
                               f'💰 Баланс: {user.coins} монет.\n'
                               f'🐹 Уровень хомяка: {user.hamster_level}\n'
                               f'🔝 Множитель: {user.multiplier_level}\n'
                               f'⏳ Пассивный доход: {user.passive_income} монет/час\n',
                               reply_markup=keyboard
                               )

        # Устанавливаем состояние
        await state.set_state(Form.main_menu)


@dp.callback_query(F.data == 'admin_panel')
async def admin_panel(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.from_user.id != 1131742460:
        await callback_query.answer("У вас нет доступа к админ-панели.")
        return

    async with SessionLocal() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()  # Получаем список всех пользователей
        stats_message = "Статистика пользователей:\n"

        for user in users:
            try:
                # Получаем информацию о пользователе
                chat_info = await bot.get_chat(user.id)
                username_link = f"@{chat_info.username}" if chat_info.username else "Без ника"
                stats_message += f"ID: {user.id}, Ник: {username_link}, Монеты: {user.coins}\n"
            except Exception as e:
                stats_message += f"ID: {user.id}, Ошибка: {str(e)}\n"

        await bot.send_message(callback_query.from_user.id, stats_message)
        await show_main_menu(callback_query.from_user.id, state)


# Обработка нажатия на кнопку "Игра: Угадай число"
@dp.callback_query(StateFilter(Form.main_menu), F.data == 'guess_number')
async def process_guess_number(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.send_message(callback_query.from_user.id, "Выберите число от 1 до 5.")

    # Устанавливаем состояние для выбора числа
    await state.set_state(Form.guess_number_choice)


# Обработка выбора числа
@dp.message(StateFilter(Form.guess_number_choice))
async def choose_number(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    chosen_number = message.text

    if not chosen_number.isdigit() or not (1 <= int(chosen_number) <= 5):
        await message.reply("Пожалуйста, выберите число от 1 до 5.")
        return

    # Сохраняем выбранное число в состоянии
    await state.update_data(chosen_number=int(chosen_number))

    await message.reply("Сколько монет вы хотите поставить?")
    # Устанавливаем состояние для выбора суммы
    await state.set_state(Form.guess_number_bet)


# Обработка выбора суммы
@dp.message(StateFilter(Form.guess_number_bet))
async def choose_bet_for_guess(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    bet_amount = message.text

    if not bet_amount.isdigit():
        await message.reply("Введите корректное число монет для ставки.")
        return

    bet_amount = int(bet_amount)

    async with SessionLocal() as session:
        user = await get_user(session, user_id)

        if bet_amount > user.coins:
            await message.reply("У вас недостаточно монет для этой ставки.")
            return

        # Получаем сохраненные данные
        state_data = await state.get_data()
        chosen_number = state_data['chosen_number']

        # Генерируем случайное число от 1 до 5
        random_number = random.randint(1, 5)

        # Определяем, угадал ли пользователь
        if chosen_number == random_number:
            user.coins += bet_amount * 5  # Умножаем ставку на 5
            await update_coins(session, user_id, user.coins)
            await message.reply(
                f"Поздравляем! Вы угадали! Случайное число: {random_number}. У вас теперь {user.coins} монет.")
        else:
            user.coins -= bet_amount
            await update_coins(session, user_id, user.coins)
            await message.reply(
                f"К сожалению, вы не угадали. Случайное число: {random_number}. У вас теперь {user.coins} монет.")

        # Возвращаемся в главное меню
        await show_main_menu(user_id, state)

# Обработка нажатия на кнопку "Игра"
@dp.callback_query(StateFilter(Form.main_menu), F.data == 'coinflip')
async def process_coinflip(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.send_message(callback_query.from_user.id, "Выберите сторону: 'орел' или 'решка'.")

    # Устанавливаем состояние для выбора стороны
    await state.set_state(Form.coinflip_side)

# Обработка выбора стороны (орел или решка)
@dp.message(StateFilter(Form.coinflip_side))
async def choose_side(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    chosen_side = message.text.lower()

    if chosen_side not in ['орел', 'решка']:
        await message.reply("Пожалуйста, выберите 'орел' или 'решка'.")
        return

    # Сохраняем выбранную сторону в состоянии
    await state.update_data(chosen_side=chosen_side)

    await message.reply("Сколько монет вы хотите поставить?")
    # Устанавливаем состояние для выбора суммы
    await state.set_state(Form.coinflip_bet)

# Обработка выбора суммы
@dp.message(StateFilter(Form.coinflip_bet))
async def choose_bet(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    bet_amount = message.text

    if not bet_amount.isdigit():
        await message.reply("Введите корректное число монет для ставки.")
        return

    bet_amount = int(bet_amount)

    async with SessionLocal() as session:
        user = await get_user(session, user_id)

        if bet_amount > user.coins:
            await message.reply("У вас недостаточно монет для этой ставки.")
            return

        # Получаем сохраненные данные
        state_data = await state.get_data()
        chosen_side = state_data['chosen_side']

        # Генерируем случайный результат (орел или решка)
        result = random.choice(['орел', 'решка'])

        # Определяем, выиграл ли пользователь
        if chosen_side == result:
            user.coins += bet_amount  # Умножаем на 2
            await update_coins(session, user_id, user.coins)
            await message.reply(f"Поздравляем! Вы выиграли! Результат: {result}. У вас теперь {user.coins} монет.")
        else:
            user.coins -= bet_amount
            await update_coins(session, user_id, user.coins)
            await message.reply(f"К сожалению, вы проиграли. Результат: {result}. У вас теперь {user.coins} монет.")

        # Возвращаемся в главное меню
        await show_main_menu(user_id, state)

@dp.callback_query(F.data == 'main_menu')
async def process_main_menu(callback_query: types.CallbackQuery, state: FSMContext):
    await show_main_menu(callback_query.from_user.id, state)


@dp.callback_query(StateFilter(Form.main_menu), F.data == 'click_hamster')
async def process_hamster_click(callback_query: types.CallbackQuery, state: FSMContext):
    # Начинаем подсчет кликов
    await state.set_state(Form.click_hamster)
    await state.update_data(clicks=0)  # Инициализация количества кликов

    # Создаем кнопки
    button1 = types.KeyboardButton(text="Клик")
    button2 = types.KeyboardButton(text="Стоп")
    keyboard = types.ReplyKeyboardMarkup(keyboard=[[button1], [button2]], resize_keyboard=True)

    await bot.send_message(
        chat_id=callback_query.from_user.id,
        text='Начинайте нажимать на кнопку "Клик".',
        reply_markup=keyboard  # Добавляем кнопки
    )


# Обработчик сообщений "Клик"
@dp.message(StateFilter(Form.click_hamster), F.text == 'Клик')
async def handle_click_message(message: types.Message, state: FSMContext):
    data = await state.get_data()
    clicks = data.get('clicks', 0) + 1  # Увеличиваем количество кликов
    await state.update_data(clicks=clicks)  # Обновляем состояние

    await message.answer(f'Вы нажали на хомячка! Всего кликов: {clicks}.')


# Обработчик сообщений "Стоп"
@dp.message(StateFilter(Form.click_hamster), F.text == 'Стоп')
async def handle_stop_message(message: types.Message, state: FSMContext):
    data = await state.get_data()
    clicks = data.get('clicks', 0)

    async with SessionLocal() as session:
        user = await get_user(session, message.from_user.id)
        if not user:
            await add_user(session, message.from_user.id)
            user = await get_user(session, message.from_user.id)

        # Обновляем количество монет
        user.coins += clicks
        user.total_tap_income += clicks # Увеличиваем счетчик заработанного от тапов
        await update_coins(session, message.from_user.id, user.coins)

    await message.answer(f'Вы остановили игру! Вы заработали {clicks} монет. У вас сейчас {user.coins} монет.')

    # Удаляем клавиатуру
    await message.answer('Игра завершена.', reply_markup=types.ReplyKeyboardRemove())

    await state.set_state(Form.click_hamster)  # Возвращаем в главное меню
    await show_main_menu(message.from_user.id, state)


@dp.callback_query(StateFilter(Form.shop), F.data == 'buy_hamster_level')
async def process_buy_hamster_level(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    async with SessionLocal() as session:
        user = await get_user(session, user_id)

        cost = (user.hamster_level + 1) ** 3

        if user.coins >= cost:  # Проверяем, достаточно ли монет
            user.coins -= cost
            user.hamster_level += 1  # Повышаем уровень хомяка
            await session.commit()
            await callback_query.answer("Вы подняли уровень хомяка!")
        else:
            await callback_query.answer("Недостаточно монет!")

@dp.callback_query(StateFilter(Form.shop), F.data == 'buy_multiplier')
async def process_buy_multiplier(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id

    async with SessionLocal() as session:
        user = await get_user(session, user_id)

        # Определите стоимость уровня множителя (например, 10 монет за уровень)
        cost = (user.multiplier_level + 1) ** 3
        if user.coins >= cost:
            user.coins -= cost
            user.multiplier_level += 1  # Увеличиваем уровень множителя
            await session.commit()
            await callback_query.answer(f"Вы купили уровень множителя! Теперь у вас уровень: {user.multiplier_level}.")
        else:
            await callback_query.answer("Недостаточно монет!")


async def give_passive_income():
    while True:
        async with SessionLocal() as session:
            users = await session.execute(select(User))
            for user in users.scalars().all():
                if user.passive_income > 0:
                    user.coins += user.passive_income  # Начисляем доход по уровню
                    user.total_passive_income += user.passive_income  # Увеличиваем счетчик заработанного от пассивного дохода
                    await update_coins(session, user.id, user.coins)

                    # Отправляем сообщение без звука и вибрации
                    await bot.send_message(
                        chat_id=user.id,
                        text=f"🎉 Вам начислено {user.passive_income} монет от пассивного дохода!",
                        disable_notification=True  # Отключаем уведомления
                    )
            await session.commit()
        await asyncio.sleep(3600)  # Каждые 60 минут

@dp.callback_query(StateFilter(Form.shop), F.data == 'buy_passive_income')
async def process_buy_passive_income(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    async with SessionLocal() as session:
        user = await get_user(session, user_id)

        # Логика стоимости для каждого уровня
        # cost = 100 * user.passive_income_level  # Стоимость растет с уровнем
        income_increase = 10 * user.passive_income_level  # Увеличение дохода зависит от уровня
        cost = 10 * ((user.passive_income_level + 1) ** 2)
        if user.passive_income_level == 0:
            income_increase = 10
            cost = 10

        if user.coins >= cost:
            user.coins -= cost
            user.passive_income += 10  # Увеличиваем доход
            user.passive_income_level += 1  # Повышаем уровень пассивного дохода
            await session.commit()
            await callback_query.answer(f"Теперь у вас пассивный доход {user.passive_income} монет/час (уровень {user.passive_income_level}).")
        else:
            await callback_query.answer(f"Недостаточно монет для покупки пассивного дохода. Нужно {cost} монет.")

# Обработка нажатия на кнопку "Игра"
@dp.callback_query(StateFilter(Form.main_menu), F.data == 'game_menu')
async def process_game_menu(callback_query: types.CallbackQuery, state: FSMContext):
    button1 = types.InlineKeyboardButton(text="🎲 Орел/Решка", callback_data='coinflip')
    button2 = types.InlineKeyboardButton(text="🔢 Угадай число", callback_data='guess_number')
    button3 = types.InlineKeyboardButton(text="🛒 Вернуться в главное меню", callback_data='main_menu')
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[button1], [button2], [button3]])

    await bot.edit_message_text(
        text="Выберите игру:",
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        reply_markup=keyboard
    )

    await state.set_state(Form.main_menu)

# Обработка нажатия на кнопку "Магазин"
@dp.callback_query(StateFilter(Form.main_menu), F.data == 'shop')
async def process_shop(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id

    state_data = await state.get_data()
    async with SessionLocal() as session:
        user = await get_user(session, user_id)

        # Определяем стоимость и уровень
        next_level_cost = 10 * ((user.passive_income_level + 1) ** 2)
        cost_buy_multiplier = (user.multiplier_level + 1) ** 3
        cost_hamster_level = (user.hamster_level + 1) ** 3

        button1 = types.InlineKeyboardButton(text=f"🏅 Купить {user.multiplier_level + 1} уровень множителя за {cost_buy_multiplier} монет",
                                             callback_data='buy_multiplier')
        button2 = types.InlineKeyboardButton(text=f"🥇 Купить {user.hamster_level + 1} уровень хомяка за {cost_hamster_level} монет",
                                             callback_data='buy_hamster_level')
        button3 = types.InlineKeyboardButton(
            text=f"💸 Купить пассивный доход {user.passive_income + 10} монет/час за {next_level_cost} монет",
            callback_data='buy_passive_income')
        button4 = types.InlineKeyboardButton(text="🛒 Вернуться в главное меню", callback_data='main_menu')
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[button1], [button2], [button3], [button4]])


        await bot.edit_message_text(
            text=f'У вас {user.coins} монет. Что вы хотите купить?',
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            reply_markup=keyboard,
        )

        # Устанавливаем состояние
        await state.set_state(Form.shop)

# Обработка нажатия на кнопку "Купить улучшение"
@dp.callback_query(StateFilter(Form.shop), F.data == 'buy_upgrade')
async def process_buy_upgrade(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id

    state_data = await state.get_data()
    async with SessionLocal() as session:
        user = await get_user(session, user_id)

        if user.coins >= 5:
            user.coins -= 5  # Списываем монеты
            await update_coins(session, user_id, user.coins)
            await bot.answer_callback_query(callback_query.id, text="Вы купили улучшение!")
        else:
            await bot.answer_callback_query(callback_query.id, text="У вас недостаточно монет!")

        await show_main_menu(user_id, state)

# Обработка нажатия на кнопку "Статистика"
@dp.callback_query(StateFilter(Form.main_menu), F.data == 'stats')
async def process_stats(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id

    state_data = await state.get_data()
    async with SessionLocal() as session:
        user = await get_user(session, user_id)

        stats_message = (
            f'**Статистика пользователя**:\n\n'
            f'💰 Текущий баланс: {user.coins}\n'
            f'💷 Заработано всего: {user.total_tap_income + user.total_passive_income}\n'
            f'💸 Заработано от тапов: {user.total_tap_income}\n'
            f'📈 Заработано от пассивного дохода: {user.total_passive_income}\n'
            f'💶 Потрачено: {user.total_tap_income + user.total_passive_income - user.coins}\n'
        )

        await bot.edit_message_text(
            text=stats_message,
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            parse_mode='Markdown'
        )
        await show_main_menu(callback_query.from_user.id, state)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    # Запуск задачи для пассивного дохода
    loop.create_task(give_passive_income())
    # Запуск бота
    loop.run_until_complete(dp.start_polling(bot, on_startup=on_startup))
