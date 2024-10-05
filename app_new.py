from aiogram import Bot, Dispatcher, types
from aiogram import F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import asyncio
from aiogram.fsm.storage.memory import MemoryStorage

API_TOKEN = '7381987351:AAGFo5oor7_tUMdZwHvjT8ltT4BvyIHvbqc'

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Хранилище данных о пользователях
user_data = {}

# Определение состояний
class UserStates(StatesGroup):
    main_menu = State()
    upgrade_hamster = State()

# Начальное меню
@dp.message(Command('start'))
async def start_command(message: types.Message):
    user_id = message.from_user.id
    user_data[user_id] = {'coins': 0, 'energy': 10, 'hamster_level': 1}
    await message.answer(
        "Добро пожаловать в Хомячий Бой! Заработай монеты, прокачай своего хомяка и следи за статистикой!")
    await main_menu(message)

async def main_menu(message: types.Message):
    await message.answer("Выберите действие:\n"
                         "1. Заработать монеты (тап)\n"
                         "2. Прокачать хомяка\n"
                         "3. Посмотреть статистику")
    await UserStates.main_menu.set()

@dp.message(F.text == '1', state=UserStates.main_menu)
async def earn_coins(message: types.Message):
    user_id = message.from_user.id
    if user_data[user_id]['energy'] > 0:
        user_data[user_id]['coins'] += 2
        user_data[user_id]['energy'] -= 1
        await message.answer(f"Вы заработали 2 монеты! У вас сейчас {user_data[user_id]['coins']} монет.")
    else:
        await message.answer("У вас недостаточно энергии. Пожалуйста, подождите немного.")

@dp.message(F.text == '2', state=UserStates.main_menu)
async def upgrade_hamster(message: types.Message):
    user_id = message.from_user.id
    await message.answer("Выберите уровень для прокачки:\n"
                         "1. Прокачать на 1 уровень (100 монет)\n"
                         "2. Прокачать на 2 уровень (200 монет)")
    await UserStates.upgrade_hamster.set()

@dp.message(F.text.in_(['1', '2']), state=UserStates.upgrade_hamster)
async def upgrade_hamster_choice(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    upgrade_cost = 100 if message.text == '1' else 200

    if user_data[user_id]['coins'] >= upgrade_cost:
        user_data[user_id]['coins'] -= upgrade_cost
        user_data[user_id]['hamster_level'] += 1
        await message.answer(
            f"Вы прокачали своего хомяка до уровня {user_data[user_id]['hamster_level']}! У вас осталось {user_data[user_id]['coins']} монет.")
    else:
        await message.answer("У вас недостаточно монет для прокачки.")

    await state.clear()
    await main_menu(message)

@dp.message(F.text == '3', state=UserStates.main_menu)
async def view_stats(message: types.Message):
    user_id = message.from_user.id
    stats = (f"Монеты: {user_data[user_id]['coins']}\n"
             f"Энергия: {user_data[user_id]['energy']}\n"
             f"Уровень хомяка: {user_data[user_id]['hamster_level']}")
    await message.answer(stats)

@dp.message(state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await main_menu(message)

if __name__ == '__main__':
    asyncio.run(dp.start_polling(bot))
